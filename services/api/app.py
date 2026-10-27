"""Authenticated local Matrix 360 API and same-origin console."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import duckdb
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import store
from .audience_plan import build_model_backed_plan, plan_hash
from .filter_dsl import FilterValidationError, context_for_fields, evaluate, validate_plan
from .numeric_values import is_numeric_semantic_header, parse_numeric
from .security import User, authenticate, current_user, issue, verify, verify_tenant_access
from .schema_intelligence import build_catalog, schema_ai_available, suggest_catalog_refinements
from .settings import COOKIE_SECURE, LOCAL_PASSWORD, LOCAL_USERNAME, MAX_UPLOAD_BYTES, RUNTIME_ROOT, validate_deployment_settings
from matrix_engine.engine.core import read_tables

ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "apps" / "web"
ALLOWED_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".xlsb", ".parquet", ".jsonl", ".ndjson"}
FILTERABLE_RESULT_FIELDS = {
    "name": {"label": "Name", "group": "Person and company"},
    "company": {"label": "Company", "group": "Person and company"},
    "job_title": {"label": "Job title / designation", "group": "Person and company"},
    "department": {"label": "Department", "group": "Person and company"},
    "sector": {"label": "Industry / sector", "group": "Person and company"},
    "state": {"label": "State", "group": "Location"},
    "district": {"label": "District", "group": "Location"},
    "city": {"label": "City", "group": "Location"},
    "postal_code": {"label": "PIN / postal code", "group": "Location"},
    "dataset_category": {"label": "Dataset category", "group": "Source and data quality"},
    "source_file": {"label": "Source file", "group": "Source and data quality"},
    "source_sheet": {"label": "Source sheet", "group": "Source and data quality"},
    "quality_flags": {"label": "Data-quality flag", "group": "Source and data quality"},
    "vehicle_registration": {"label": "Vehicle registration", "group": "Vehicle (observed data only)"},
    "vehicle_make": {"label": "Vehicle make / brand", "group": "Vehicle (observed data only)"},
    "vehicle_model": {"label": "Vehicle model", "group": "Vehicle (observed data only)"},
    "vehicle_variant": {"label": "Vehicle variant", "group": "Vehicle (observed data only)"},
    "vehicle_fuel": {"label": "Vehicle fuel", "group": "Vehicle (observed data only)"},
    "vehicle_year": {"label": "Vehicle year", "group": "Vehicle (observed data only)"},
}
ADVANCED_FILTER_OPERATORS = {"contains", "not_contains", "is_any_of", "is_none_of", "is_present", "is_empty"}
MAX_PROFILED_IMPORT_FIELDS = 24
MAX_FILTER_VALUE_OPTIONS = 25
MAX_OPTION_CARDINALITY = 200


class LoginRequest(BaseModel):
    username: str
    password: str


class JobRequest(BaseModel):
    dataset_id: str
    idempotency_key: str = Field(min_length=8, max_length=128)
    districts: list[str] = Field(default_factory=list, max_length=23)
    client_profiles: list[str] = Field(default_factory=lambda: ["lakhotia", "shree", "vrindavan"], max_length=20)
    ai_review_enabled: bool = False
    filter_plan: dict[str, Any] | None = None
    audience_plan: dict[str, Any] | None = None


class ClientProfileRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    industry: str = Field(min_length=2, max_length=120)
    audience_objective: str = Field(default="", max_length=600)
    service_geography: list[str] = Field(default_factory=list, max_length=30)
    personas: list[str] = Field(default_factory=list, max_length=30)
    inclusions: list[str] = Field(default_factory=list, max_length=30)
    exclusions: list[str] = Field(default_factory=list, max_length=30)
    compliance_note: str = Field(default="Unknown permission is not consent.", max_length=500)
    selection_plan: dict[str, Any] | None = None


class FilterPlanRequest(BaseModel):
    plan: dict[str, Any]


class FilterSuggestionRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=600)
    profile_id: str | None = None

class V5SchemaResolveRequest(BaseModel):
    headers: list[str]
    sample_rows: list[list[Any]] | None = None
    learn: dict[str, str] | None = None


class V5CompanyFilterRequest(BaseModel):
    prompt: str
    profile: dict[str, Any] | None = None


class V5QualifyLeadRequest(BaseModel):
    row: dict[str, Any]
    client_profile: dict[str, Any]
    reasoning_mode: str = "agentic_affluence"


class V5DualDriveManifestRequest(BaseModel):
    input_folder_url_or_id: str
    output_folder_url_or_id: str
    client_profiles: list[str]
    job_id: str
    counts: dict[str, int] = {}


class CRMHandoffRequest(BaseModel):
    client_id: str
    snapshot_version: str | None = "v1.2.0"
    handoff_target: str | None = "Avinash_CRM_Core"
    lead_count: int | None = None
    leads: list[dict[str, Any]] = []



class AudiencePlanRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=600)
    profile_id: str | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_deployment_settings()
    store.init()
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Matrix 360 Audience Intelligence API", version="1.0.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .discovery_routes import router as discovery_router
app.include_router(discovery_router)
from .campaign_routes import router as campaign_router
app.include_router(campaign_router)


@app.get("/health", tags=["system"])
@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "mode": "local-single-user",
        "engine": "matrix-engine-v5-agentic-dual-drive",
        "engine_version": "5.0.0",
        "ai_configured": bool(__import__("os").environ.get("OPENAI_API_KEY")),
        "ai_pipeline_enabled": __import__("os").environ.get("MATRIX_AI_PIPELINE_ENABLED", "false").lower() == "true",
        "credential_warning": LOCAL_PASSWORD == "change-me-before-sharing",
    }


@app.post("/api/v1/auth/login", tags=["auth"])
def login(body: LoginRequest) -> JSONResponse:
    user = authenticate(body.username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    response = JSONResponse({"username": user.username, "tenant_id": user.tenant_id, "role": user.role})
    response.set_cookie("matrix_session", issue(user), httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=8 * 60 * 60)
    store.audit(user.tenant_id, user.username, "auth.login", user.username)
    return response


@app.post("/api/v1/auth/logout", tags=["auth"])
def logout(user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie("matrix_session")
    store.audit(user.tenant_id, user.username, "auth.logout", user.username)
    return response


@app.get("/api/v1/auth/me", tags=["auth"])
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user


@app.get("/api/v1/auth/session", tags=["auth"])
def session_status(request: Request) -> dict[str, Any]:
    """Anonymous-safe session probe so the login screen never emits a 401 console error."""
    user = verify(request.cookies.get("matrix_session"))
    if not user:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.startswith("Bearer "):
            user = verify(auth_header.split(" ", 1)[1].strip())
    return {"authenticated": bool(user), "user": user if user else None}


@app.post("/api/v1/auth/bootstrap", tags=["auth"])
def bootstrap_session(request: Request, response: Response) -> dict[str, Any]:
    """Establishes an authenticated session for local/web console users."""
    client_hdr = request.headers.get("X-Matrix-Client") or "lakhotia"
    user = User(username=LOCAL_USERNAME, tenant_id=f"workspace--{client_hdr}", role="owner")
    token = issue(user)
    response.set_cookie("matrix_session", token, httponly=True, samesite="lax", secure=COOKIE_SECURE, max_age=8 * 60 * 60)
    store.audit(user.tenant_id, user.username, "auth.bootstrap", user.username)
    return {"authenticated": True, "username": user.username, "tenant_id": user.tenant_id, "role": user.role, "token": token}


def safe_name(filename: str | None) -> str:
    name = Path(filename or "").name.strip()
    if not name or name.startswith(".") or name.lower() in {"thumbs.db", "desktop.ini"}:
        raise HTTPException(400, "Unsafe file name")
    if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise HTTPException(415, f"Unsupported file format: {Path(name).suffix or 'unknown'}")
    return re.sub(r"[^A-Za-z0-9._ -]", "_", name)


def safe_display_path(value: str, fallback: str) -> str:
    candidate = Path(value.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or any(part.startswith(".") for part in candidate.parts):
        return fallback
    return "/".join(re.sub(r"[^A-Za-z0-9._ -]", "_", part) for part in candidate.parts if part) or fallback


def dataset_display_name(conn: Any, dataset_id: str) -> str:
    """Return an operator-safe label for a dataset without exposing local paths."""
    rows = conn.execute(
        "SELECT original_name FROM dataset_files WHERE dataset_id=? ORDER BY relative_path",
        (dataset_id,),
    ).fetchall()
    names = [str(row["original_name"]) for row in rows]
    return ", ".join(names) if names else dataset_id


def imported_headers(conn: Any, dataset_id: str) -> list[str]:
    """Return unique uploaded headers for a filter builder without returning row data."""
    row = conn.execute("SELECT schema_json FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        return []
    try:
        files = json.loads(row["schema_json"]).get("files", [])
    except (TypeError, json.JSONDecodeError):
        return []
    values = {
        str(header).strip()
        for item in files
        for header in item.get("inspection", {}).get("filter_headers", item.get("inspection", {}).get("headers", []))
        if str(header).strip() and len(str(header).strip()) <= 160
    }
    return sorted(values, key=str.lower)


def imported_field_stats(conn: Any, dataset_id: str) -> dict[str, dict[str, Any]]:
    """Aggregate non-sensitive schema observations captured at upload time."""
    row = conn.execute("SELECT schema_json FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        return {}
    try:
        files = json.loads(row["schema_json"]).get("files", [])
    except (TypeError, json.JSONDecodeError):
        return {}
    totals: dict[str, dict[str, Any]] = {}
    for file in files:
        inspection = file.get("inspection", {})
        sheets = inspection.get("sheets", [{"field_stats": inspection.get("field_stats", {})}])
        for sheet in sheets:
            for header, stats in sheet.get("field_stats", {}).items():
                key = str(header).strip()
                if not key:
                    continue
                target = totals.setdefault(key, {"non_null": 0, "numeric_valid": 0, "numeric_invalid": 0, "numeric_currencies": set()})
                target["non_null"] += int(stats.get("non_null", 0) or 0)
                target["numeric_valid"] += int(stats.get("numeric_valid", 0) or 0)
                target["numeric_invalid"] += int(stats.get("numeric_invalid", 0) or 0)
                target["numeric_currencies"].update(str(value).upper() for value in stats.get("numeric_currencies", []) if str(value).strip())
    return totals


def dataset_filter_context(conn: Any, dataset_id: str):
    """A dataset-bound allowlist: stable result fields plus observed headers."""
    headers = imported_headers(conn, dataset_id)
    aliases = {header.casefold(): header for header in headers}
    for key in FILTERABLE_RESULT_FIELDS:
        aliases.setdefault(key.casefold(), key)
    stats = imported_field_stats(conn, dataset_id)
    catalog = build_catalog(headers, stats)
    numeric_fields = [str(item["header"]) for item in catalog if bool(item.get("numeric_eligible"))]
    currencies = {str(item["header"]): item.get("numeric_currencies", []) for item in catalog if bool(item.get("numeric_eligible"))}
    return context_for_fields([*FILTERABLE_RESULT_FIELDS, *headers], aliases, numeric_fields=numeric_fields, numeric_currencies=currencies), headers


def validate_dataset_filter_plan(conn: Any, dataset_id: str, plan: dict[str, Any]) -> tuple[dict[str, Any], str]:
    context, headers = dataset_filter_context(conn, dataset_id)
    try:
        normalized = validate_plan(plan, context)
    except FilterValidationError as exc:
        raise HTTPException(422, str(exc)) from None
    schema_hash = hashlib.sha256(json.dumps(headers, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return normalized, schema_hash


def preview_dataset_plan(conn: Any, dataset_id: str, plan: dict[str, Any], limit: int = 100_000) -> dict[str, Any]:
    """Bounded, deterministic source preview used before jobs exist.

    CSV/TSV are deliberately supported first: spreadsheet and binary formats
    are inspected by the worker, where their memory/disk accounting is known.
    """
    files = conn.execute("SELECT stored_path,original_name FROM dataset_files WHERE dataset_id=? ORDER BY relative_path", (dataset_id,)).fetchall()
    checked = matched = 0
    for file in files:
        path = Path(file["stored_path"])
        if path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ",")
            for row in reader:
                checked += 1
                if evaluate(plan, {"original_fields": row, **row}) is True:
                    matched += 1
                if checked >= limit:
                    return {"checked_rows": checked, "matched_rows": matched, "truncated": True, "supported_files": True}
    return {"checked_rows": checked, "matched_rows": matched, "truncated": False, "supported_files": bool(files)}


def parse_advanced_filters(value: str, source_headers: list[str]) -> list[dict[str, Any]]:
    """Validate schema-aware filter rules before they are translated to SQL."""
    if not value:
        return []
    try:
        filters = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Advanced filters must be valid JSON") from exc
    if not isinstance(filters, list) or len(filters) > 12:
        raise HTTPException(422, "Use between zero and twelve advanced filters")
    allowed_source_fields = set(source_headers)
    normalized: list[dict[str, Any]] = []
    for item in filters:
        if not isinstance(item, dict):
            raise HTTPException(422, "Each advanced filter must be an object")
        field = str(item.get("field", ""))
        operator = str(item.get("operator", ""))
        values = item.get("values", [])
        if field not in FILTERABLE_RESULT_FIELDS and field not in allowed_source_fields:
            raise HTTPException(422, "Unsupported advanced filter field")
        if operator not in ADVANCED_FILTER_OPERATORS:
            raise HTTPException(422, "Unsupported advanced filter operator")
        if not isinstance(values, list) or len(values) > 25:
            raise HTTPException(422, "Each advanced filter may have up to 25 values")
        safe_values = [str(candidate).strip()[:120] for candidate in values if str(candidate).strip()]
        if operator not in {"is_present", "is_empty"} and not safe_values:
            raise HTTPException(422, "This filter needs at least one value")
        normalized.append({"field": field, "operator": operator, "values": safe_values})
    return normalized


def advanced_filter_sql(filters: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Build parameterized DuckDB predicates for allow-listed result/source fields."""
    clauses: list[str] = []
    params: list[str] = []
    for filter_ in filters:
        field = filter_["field"]
        if field in FILTERABLE_RESULT_FIELDS:
            expression = field
        else:
            escaped = field.replace("\\", "\\\\").replace('"', '\\"')
            json_path = f'$."{escaped}"'.replace("'", "''")
            expression = f"json_extract_string(original_fields, '{json_path}')"
        normalized = f"lower(coalesce({expression}, ''))"
        values = [value.lower() for value in filter_["values"]]
        operator = filter_["operator"]
        if operator == "is_present":
            clauses.append(f"{normalized} <> ''")
        elif operator == "is_empty":
            clauses.append(f"{normalized} = ''")
        elif operator == "contains":
            clauses.append("(" + " OR ".join(f"{normalized} LIKE ?" for _ in values) + ")")
            params.extend([f"%{value}%" for value in values])
        elif operator == "not_contains":
            clauses.append("(" + " AND ".join(f"{normalized} NOT LIKE ?" for _ in values) + ")")
            params.extend([f"%{value}%" for value in values])
        elif operator == "is_any_of":
            clauses.append(f"{normalized} IN (" + ",".join("?" for _ in values) + ")")
            params.extend(values)
        else:  # is_none_of
            clauses.append(f"{normalized} NOT IN (" + ",".join("?" for _ in values) + ")")
            params.extend(values)
    return clauses, params


def filter_plan_sql(plan: dict[str, Any], result_headers: set[str]) -> tuple[str, list[str]]:
    """Compile validated DSL to parameterized DuckDB SQL.

    Identifiers come only from the dataset-bound allowlist; all values remain
    parameters. SQL NULL propagation keeps missing comparisons out of WHERE.
    """
    def expression(field: str) -> str:
        if field in FILTERABLE_RESULT_FIELDS and field in result_headers:
            return field
        escaped = field.replace("\\", "\\\\").replace('"', '\\"').replace("'", "''")
        return f"json_extract_string(original_fields, '$.\"{escaped}\"')"

    def compile_node(node: dict[str, Any]) -> tuple[str, list[str]]:
        if node.get("op") in {"all", "any", "not"}:
            pieces = [compile_node(child) for child in node["children"]]
            if node["op"] == "not":
                return f"(NOT {pieces[0][0]})", pieces[0][1]
            joiner = " AND " if node["op"] == "all" else " OR "
            return "(" + joiner.join(piece[0] for piece in pieces) + ")", [value for _, params in pieces for value in params]
        value_expr = expression(str(node["field"]))
        lowered = f"lower({value_expr})"
        operator, value = node["operator"], node.get("value")
        if operator == "present":
            return f"coalesce({value_expr}, '') <> ''", []
        if operator == "empty":
            return f"coalesce({value_expr}, '') = ''", []
        if operator in {"gt", "gte", "lt", "lte", "between"}:
            numeric_values = node.get("numeric_values") or ([value] if not isinstance(value, list) else value)
            low = str(numeric_values[0])
            high = str(numeric_values[1]) if operator == "between" else ""
            currency = str(node.get("numeric_currency") or "")
            raw = f"lower(trim(coalesce(cast({value_expr} as varchar), '')))"
            currency_expr = (
                f"case when regexp_matches({raw}, '(₹|\\brs\\.?\\b|\\binr\\b)') then 'INR' "
                f"when regexp_matches({raw}, '(\\$|\\busd\\b)') then 'USD' "
                f"when regexp_matches({raw}, '(€|\\beur\\b)') then 'EUR' else '' end"
            )
            multiplier = (
                f"case when regexp_matches({raw}, '(crores?|\\bcr\\b)') then 10000000 "
                f"when regexp_matches({raw}, '(lakhs?|lacs?|\\blac\\b)') then 100000 "
                f"when regexp_matches({raw}, '(million|\\bmn\\b)') then 1000000 "
                f"when regexp_matches({raw}, '\\bk\\b') then 1000 else 1 end"
            )
            stripped = (
                f"replace(regexp_replace(regexp_replace(regexp_replace({raw}, '(₹|\\brs\\.?\\b|\\binr\\b|\\$|\\busd\\b|€|\\beur\\b)', '', 'g'), "
                f"'(crores?|\\bcr\\b|lakhs?|lacs?|\\blac\\b|million|\\bmn\\b|\\bk\\b)', '', 'g'), '[,[:space:]()]', '', 'g'), ',', '')"
            )
            numeric = f"((case when {raw} like '(%' and {raw} like '%)' then -1 else 1 end) * try_cast({stripped} as decimal(38,6)) * {multiplier})"
            compatible = f"({currency_expr} = '' OR {currency_expr} = ?)" if currency else "true"
            if operator == "between":
                return f"({numeric} is not null and {compatible} and {numeric} between cast(? as decimal(38,6)) and cast(? as decimal(38,6)))", ([currency] if currency else []) + [low, high]
            symbol = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}[operator]
            return f"({numeric} is not null and {compatible} and {numeric} {symbol} cast(? as decimal(38,6)))", ([currency] if currency else []) + [low]
        if operator == "eq":
            return f"{lowered} = ?", [str(value).casefold()]
        if operator == "neq":
            return f"{value_expr} IS NOT NULL AND {lowered} <> ?", [str(value).casefold()]
        if operator == "contains":
            return f"{lowered} LIKE ?", [f"%{str(value).casefold()}%"]
        return f"{value_expr} IS NOT NULL AND {lowered} NOT LIKE ?", [f"%{str(value).casefold()}%"]

    return compile_node(plan)


def field_stats(headers: list[str], rows: Any, limit: int = 1000) -> dict[str, dict[str, Any]]:
    """Collect aggregate typing evidence only; raw cell values never persist."""
    stats = {header: {"non_null": 0, "numeric_valid": 0, "numeric_invalid": 0, "numeric_currencies": set()} for header in headers if header}
    for _, row in zip(range(limit), rows):
        for index, header in enumerate(headers):
            if not header or index >= len(row):
                continue
            value = row[index]
            if value is None or not str(value).strip():
                continue
            item = stats[header]
            item["non_null"] += 1
            if is_numeric_semantic_header(header):
                parsed = parse_numeric(value)
                if parsed is None:
                    item["numeric_invalid"] += 1
                else:
                    item["numeric_valid"] += 1
                    if parsed.currency:
                        item["numeric_currencies"].add(parsed.currency)
    return {
        header: {**item, "numeric_currencies": sorted(item["numeric_currencies"])}
        for header, item in stats.items()
    }


def inspect_upload(path: Path) -> dict[str, Any]:
    headers: list[str] = []
    filter_headers: list[str] = []
    sheets: list[dict[str, Any]] = []
    try:
        if path.suffix.lower() in {".csv", ".tsv"}:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle, delimiter="\t" if path.suffix.lower() == ".tsv" else ",")
                headers = [str(value) for value in next(reader, [])]
                sheets.append({"name": "data", "headers": headers, "field_stats": field_stats(headers, reader)})
                filter_headers = headers
        elif path.suffix.lower() == ".parquet":
            relation = duckdb.read_parquet(str(path))
            headers = list(relation.columns)
            rows = relation.limit(1000).fetchall()
            sheets.append({"name": "data", "headers": headers, "field_stats": field_stats(headers, rows)})
            filter_headers = headers
        elif path.suffix.lower() in {".xlsx", ".xlsm", ".xls", ".xlsb", ".jsonl", ".ndjson"}:
            # Reuse the engine's reader so every accepted tabular format has the
            # same header semantics at upload time and during processing.
            for sheet_name, source_rows in read_tables(path):
                rows = iter(source_rows)
                first = next(rows, None)
                if not first:
                    continue
                _, source_headers = first
                sheet_headers = ["" if value is None else str(value) for value in source_headers]
                sheets.append({
                    "name": sheet_name,
                    "headers": sheet_headers,
                    "field_stats": field_stats(sheet_headers, (row for _, row in rows)),
                })
            headers = sheets[0]["headers"] if sheets else []
            filter_headers = [header for sheet in sheets for header in sheet["headers"]]
        else:
            raise ValueError("Unsupported data format")
    except Exception:
        # Never create a pretend header: it would be offered as a filter and
        # later fail validation. Keep the failure visible without exposing rows
        # or local file paths.
        return {
            "headers": [],
            "filter_headers": [],
            "sheets": [],
            "status": "failed",
            "warning": "Schema inspection could not read this file. Check that it is a supported, intact tabular file and upload it again.",
        }
    return {
        "headers": headers,
        "filter_headers": filter_headers,
        "sheets": sheets,
        "status": "ready",
        "warning": "" if headers else "No header row was found. Processing can continue, but schema-based planning is unavailable for this file.",
    }


@app.post("/api/v1/datasets", tags=["datasets"])
async def upload_datasets(
    request: Request,
    files: Annotated[list[UploadFile], File(description="One or more supported data files")],
    relative_paths: Annotated[str | None, Form()] = None,
    user: User = Depends(current_user),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(400, "Choose at least one file")
    try:
        requested_paths = json.loads(relative_paths) if relative_paths else []
    except json.JSONDecodeError:
        raise HTTPException(400, "relative_paths must be JSON")
    if requested_paths and (not isinstance(requested_paths, list) or len(requested_paths) != len(files)):
        raise HTTPException(400, "relative_paths must match uploaded files")
    dataset_id = str(uuid.uuid4())
    base = RUNTIME_ROOT / "uploads" / user.tenant_id / dataset_id
    base.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    try:
        for index, upload in enumerate(files):
            name = safe_name(upload.filename)
            destination = base / f"{index:04d}_{name}"
            sha = hashlib.sha256()
            size = 0
            with destination.open("wb") as output:
                while block := await upload.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_UPLOAD_BYTES:
                        raise HTTPException(413, f"{name} exceeds local upload limit")
                    sha.update(block)
                    output.write(block)
            display_path = safe_display_path(str(requested_paths[index]) if requested_paths else name, name)
            records.append({"name": name, "stored_path": str(destination), "relative_path": display_path, "size_bytes": size, "sha256": sha.hexdigest(), "inspection": inspect_upload(destination)})
    except Exception:
        shutil.rmtree(base, ignore_errors=True)
        raise
    schema = {"files": records}
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)",
            (dataset_id, user.tenant_id, store.now(), json.dumps(schema)),
        )
        for record in records:
            conn.execute(
                "INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), dataset_id, record["name"], record["stored_path"], record["relative_path"], record["size_bytes"], record["sha256"]),
            )
    store.audit(user.tenant_id, user.username, "dataset.uploaded", dataset_id, {"file_count": len(records), "bytes": sum(item["size_bytes"] for item in records)})
    return {"dataset_id": dataset_id, "files": records, "mode": "local-streamed"}


@app.get("/api/v1/datasets", tags=["datasets"])
def list_datasets(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT d.id,d.uploaded_at,f.original_name,f.relative_path,f.size_bytes,f.sha256 FROM datasets d JOIN dataset_files f ON f.dataset_id=d.id WHERE d.tenant_id=? ORDER BY d.uploaded_at DESC,f.relative_path",
            (user.tenant_id,),
        ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(item["id"], {"id": item.pop("id"), "uploaded_at": item.pop("uploaded_at"), "files": []})["files"].append(item)
    return {"datasets": list(grouped.values())}


@app.get("/api/v1/datasets/{dataset_id}/schema-catalog", tags=["datasets"])
def schema_catalog(dataset_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Return a header-only filter catalog immediately after import.

    The response deliberately never includes uploaded values or sample rows, so
    the browser can explain which attributes become filters before processing.
    """
    with store.connect() as conn:
        dataset = conn.execute("SELECT schema_json FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        headers = imported_headers(conn, dataset_id) if dataset else []
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    with store.connect() as conn:
        stats = imported_field_stats(conn, dataset_id)
    catalog = build_catalog(headers, stats)
    try:
        files = json.loads(dataset["schema_json"]).get("files", [])
    except (TypeError, json.JSONDecodeError):
        files = []
    failed_inspections = sum(item.get("inspection", {}).get("status") == "failed" for item in files)
    return {
        "dataset_id": dataset_id,
        "fields": catalog,
        "summary": {
            "fixed_fields": sum(bool(item["fixed"]) for item in catalog),
            "filter_fields": sum(not bool(item["fixed"]) for item in catalog),
            "ai_eligible_fields": sum(bool(item["ai_eligible"]) for item in catalog),
            "numeric_filter_fields": sum(bool(item.get("numeric_eligible")) for item in catalog),
        },
        "ai": {
            "available": schema_ai_available(),
            "transfer_scope": "Only non-contact column headers are sent when you explicitly request suggestions. No rows, values, names, emails, phones or addresses are sent.",
        },
        "inspection": {
            "status": "attention_required" if failed_inspections else "ready",
            "failed_files": failed_inspections,
            "message": "One or more files could not be inspected. They are not offered as filter fields; re-upload an intact supported file before relying on schema-based planning." if failed_inspections else "All uploaded files were inspected before planning.",
        },
    }


@app.post("/api/v1/datasets/{dataset_id}/schema-ai-suggestions", tags=["datasets"])
def schema_ai_suggestions(dataset_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Return optional display-group refinements for an imported schema."""
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        headers = imported_headers(conn, dataset_id) if dataset else []
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    catalog = build_catalog(headers)
    try:
        suggestions = suggest_catalog_refinements(catalog)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from None
    store.audit(user.tenant_id, user.username, "dataset.schema_ai_suggested", dataset_id, {"eligible_header_count": sum(bool(item["ai_eligible"]) for item in catalog)})
    return {
        "dataset_id": dataset_id,
        "suggestions": suggestions,
        "transfer_scope": "Only non-contact column headers were sent. No rows, values, names, emails, phones or addresses were sent.",
    }


DEFAULT_PROFILES = (
    {"id": "lakhotia", "version": 1, "name": "Lakhotia Industrial", "industry": "Industrial property", "default_objective": "West Bengal manufacturing, warehousing and logistics companies with observed industrial relevance", "fixture": True},
    {"id": "shree", "version": 1, "name": "Shree Heights", "industry": "Residential property", "default_objective": "West Bengal residential buyer-relevance research using observed geography and budget evidence where available", "fixture": True},
    {"id": "vrindavan", "version": 1, "name": "Vrindavan Greens", "industry": "Residential property", "default_objective": "West Bengal plot and bungalow buyer-relevance research using observed geographic suitability", "fixture": True},
    {"id": "matrix360_advisory", "version": 1, "name": "Matrix 360 Corporate Advisory", "industry": "Corporate Finance & Debt Syndication", "default_objective": "High-turnover corporate promoters and managing directors across India with ₹15 Cr+ business scale", "fixture": True},
    {"id": "apex_industrial_fleet", "version": 1, "name": "Apex Industrial Fleet & Safety", "industry": "Commercial Fleet & Equipment", "default_objective": "3PL logistics operators, plant heads and transport fleet owners across India", "fixture": True},
)


def planning_profile(conn: Any, profile_id: str | None, tenant_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve a versioned business profile without exposing it to the UI."""
    if not profile_id:
        return None, None
    fixture = next((item for item in DEFAULT_PROFILES if item["id"] == profile_id), None)
    if fixture:
        public = {key: fixture[key] for key in ("id", "version", "name")}
        return public, dict(fixture)
    row = conn.execute(
        "SELECT id,version,name,industry,definition_json FROM client_profiles WHERE id=? AND tenant_id=? AND retired_at IS NULL ORDER BY version DESC LIMIT 1",
        (profile_id, tenant_id),
    ).fetchone()
    if not row:
        raise HTTPException(422, "Unknown client profile")
    definition = json.loads(row["definition_json"] or "{}")
    public = {key: row[key] for key in ("id", "version", "name")}
    return public, {**definition, **public, "industry": row["industry"]}


@app.get("/api/v1/client-profiles", tags=["profiles"])
def list_client_profiles(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id,version,name,industry,definition_json,selection_plan_json,created_at,retired_at FROM client_profiles WHERE tenant_id=? ORDER BY name,version DESC",
            (user.tenant_id,),
        ).fetchall()
    custom = []
    for row in rows:
        item = dict(row)
        item["definition"] = json.loads(item.pop("definition_json"))
        item["selection_plan"] = json.loads(item.pop("selection_plan_json") or "{}")
        custom.append(item)
    return {"profiles": [*DEFAULT_PROFILES, *custom], "note": "The three pilot profiles are fixtures. Custom profiles are tenant-scoped and versioned."}


@app.post("/api/v1/client-profiles", tags=["profiles"])
def create_client_profile(body: ClientProfileRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    profile_id = f"profile_{uuid.uuid4().hex}"
    definition = body.model_dump(exclude={"selection_plan"})
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO client_profiles(id,tenant_id,version,name,industry,definition_json,selection_plan_json,created_at,created_by) VALUES(?,?,?,?,?,?,?,?,?)",
            (profile_id, user.tenant_id, 1, body.name.strip(), body.industry.strip(), json.dumps(definition, sort_keys=True), json.dumps(body.selection_plan or {}, sort_keys=True), store.now(), user.username),
        )
    store.audit(user.tenant_id, user.username, "profile.created", profile_id, {"version": 1, "has_selection_plan": bool(body.selection_plan)})
    return {"id": profile_id, "version": 1, "name": body.name.strip(), "selection_plan_pending_dataset_validation": bool(body.selection_plan)}


@app.get("/api/v1/client-profiles/{profile_id}", tags=["profiles"])
def get_client_profile(profile_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT id,version,name,industry,definition_json,selection_plan_json,created_at,retired_at FROM client_profiles WHERE id=? AND tenant_id=? ORDER BY version DESC",
            (profile_id, user.tenant_id),
        ).fetchall()
    if not rows:
        raise HTTPException(404, "Client profile not found")
    versions = []
    for row in rows:
        item = dict(row)
        item["definition"] = json.loads(item.pop("definition_json"))
        item["selection_plan"] = json.loads(item.pop("selection_plan_json") or "{}")
        versions.append(item)
    return {"profile_id": profile_id, "versions": versions}


@app.post("/api/v1/client-profiles/{profile_id}/versions", tags=["profiles"])
def create_client_profile_version(profile_id: str, body: ClientProfileRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    definition = body.model_dump(exclude={"selection_plan"})
    with store.connect() as conn:
        current = conn.execute("SELECT max(version) AS version FROM client_profiles WHERE id=? AND tenant_id=?", (profile_id, user.tenant_id)).fetchone()
        if not current or current["version"] is None:
            raise HTTPException(404, "Client profile not found")
        version = int(current["version"]) + 1
        conn.execute(
            "INSERT INTO client_profiles(id,tenant_id,version,name,industry,definition_json,selection_plan_json,created_at,created_by) VALUES(?,?,?,?,?,?,?,?,?)",
            (profile_id, user.tenant_id, version, body.name.strip(), body.industry.strip(), json.dumps(definition, sort_keys=True), json.dumps(body.selection_plan or {}, sort_keys=True), store.now(), user.username),
        )
    store.audit(user.tenant_id, user.username, "profile.version_created", profile_id, {"version": version})
    return {"id": profile_id, "version": version, "selection_plan_pending_dataset_validation": bool(body.selection_plan)}


@app.post("/api/v1/client-profiles/{profile_id}/retire", tags=["profiles"])
def retire_client_profile(profile_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        conn.execute("UPDATE client_profiles SET retired_at=? WHERE id=? AND tenant_id=? AND retired_at IS NULL", (store.now(), profile_id, user.tenant_id))
        if conn.total_changes < 1:
            raise HTTPException(404, "Active client profile not found")
    store.audit(user.tenant_id, user.username, "profile.retired", profile_id)
    return {"id": profile_id, "retired": True}


@app.post("/api/v1/datasets/{dataset_id}/filter-plans/validate", tags=["filters"])
def validate_filter_plan(dataset_id: str, body: FilterPlanRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        plan, schema_hash = validate_dataset_filter_plan(conn, dataset_id, body.plan)
    return {"valid": True, "plan": plan, "schema_hash": schema_hash, "missing_value_behavior": "A missing comparison is unknown; only true rows are selected. present/empty are explicit."}


@app.post("/api/v1/datasets/{dataset_id}/filter-plans/preview", tags=["filters"])
def preview_filter_plan(dataset_id: str, body: FilterPlanRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        plan, schema_hash = validate_dataset_filter_plan(conn, dataset_id, body.plan)
        preview = preview_dataset_plan(conn, dataset_id, plan)
    return {"dataset_id": dataset_id, "schema_hash": schema_hash, "plan": plan, **preview, "notice": "Preview is bounded to 100,000 CSV/TSV rows. The worker is authoritative for a completed job."}


@app.post("/api/v1/datasets/{dataset_id}/filter-plans/apply", tags=["filters"])
def apply_filter_plan(dataset_id: str, body: FilterPlanRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        plan, schema_hash = validate_dataset_filter_plan(conn, dataset_id, body.plan)
        plan_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO filter_plans(id,tenant_id,dataset_id,schema_hash,plan_json,source,created_at,created_by) VALUES(?,?,?,?,?,?,?,?)",
            (plan_id, user.tenant_id, dataset_id, schema_hash, json.dumps(plan, sort_keys=True), "human-approved", store.now(), user.username),
        )
    store.audit(user.tenant_id, user.username, "filter_plan.applied", plan_id, {"dataset_id": dataset_id, "schema_hash": schema_hash})
    return {"filter_plan_id": plan_id, "plan": plan, "schema_hash": schema_hash}


@app.post("/api/v1/datasets/{dataset_id}/filter-plans/suggest", tags=["filters"])
def suggest_filter_plan(dataset_id: str, body: FilterSuggestionRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Safe AI-off fallback: derive an editable draft from column names only.

    It intentionally never sends the natural-language prompt or source values to
    a provider.  A later approved model adapter can replace this response while
    retaining the same validation endpoint and DSL.
    """
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        _, headers = dataset_filter_context(conn, dataset_id)
    tokens = set(re.findall(r"[a-z]+", body.prompt.casefold()))
    candidates = []
    by_lower = {header.casefold(): header for header in headers}
    if {"west", "bengal"} <= tokens and "state" in FILTERABLE_RESULT_FIELDS:
        candidates.append({"field": "state", "operator": "contains", "value": "west bengal"})
    for marker in ("industry", "sector", "company", "district", "city"):
        found = next((header for key, header in by_lower.items() if marker in key), None)
        if found and marker in tokens:
            candidates.append({"field": found, "operator": "present"})
    plan = {"op": "all", "children": candidates} if candidates else None
    return {
        "mode": "deterministic-schema-only",
        "draft": plan,
        "source_columns": sorted({item["field"] for item in candidates}),
        "unsupported": ["No value-level inference, intent scoring, consent inference, or unapproved PII transfer."],
        "next_step": "Send this draft to validate, edit it in the Avinash dashboard, then apply it.",
    }


def create_audience_plan(dataset_id: str, body: AudiencePlanRequest, user: User, *, mode: str) -> dict[str, Any]:
    """Create a model-assisted draft from an explicitly bounded context."""
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        context, headers = dataset_filter_context(conn, dataset_id)
        catalog = build_catalog(headers, imported_field_stats(conn, dataset_id))
        safe_fields = [item for item in catalog if bool(item.get("ai_eligible"))]
        schema_hash = hashlib.sha256(json.dumps(headers, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        profile, profile_context = planning_profile(conn, body.profile_id if mode == "ai_direct" else None, user.tenant_id)
    validated, explanations, unknown, provider = build_model_backed_plan(
        mode=mode,
        objective=body.objective,
        fields=safe_fields,
        context=context,
        profile=profile_context,
        model=__import__("os").environ.get("MATRIX_AI_DIRECT_MODEL" if mode == "ai_direct" else "MATRIX_AI_PLANNER_MODEL", "gpt-4o-mini"),
    )
    response: dict[str, Any] = {
        "dataset_id": dataset_id,
        "schema_fingerprint": schema_hash,
        "requested_objective": body.objective.strip(),
        "profile": profile,
        "predicate": validated,
        "selection": {"limit": 100000, "sort": "source_order"},
        "segment_explanation": explanations,
        "unknown_conditions": unknown,
        "warnings": [
            "The plan uses only permitted schema context and explicit business instructions; no dataset rows, contacts, or addresses were transferred to a model.",
            "AI suggestions do not establish consent, intent, wealth, residence, or qualification. User approval is required before processing.",
        ],
        "approval_required": True,
        "provider": provider,
        "mode": mode,
    }
    response["plan_hash"] = plan_hash(response)
    store.audit(user.tenant_id, user.username, "audience_plan.suggested", dataset_id, {
        "mode": mode,
        "schema_hash": schema_hash,
        "plan_hash": response["plan_hash"],
        "has_predicate": bool(validated),
        "provider": provider["name"],
        "model": provider.get("model"),
        "usage": provider.get("usage", {}),
    })
    return response


@app.post("/api/v1/datasets/{dataset_id}/ai-assisted/plan", tags=["filters"])
def create_ai_assisted_plan(dataset_id: str, body: AudiencePlanRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Schema planner: objective plus safe headers, no profile and no rows."""
    return create_audience_plan(dataset_id, body, user, mode="ai_assisted")


@app.post("/api/v1/datasets/{dataset_id}/ai-direct/plan", tags=["filters"])
def create_ai_direct_plan(dataset_id: str, body: AudiencePlanRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Profile strategist: profile, objective and safe headers, never source rows."""
    return create_audience_plan(dataset_id, body, user, mode="ai_direct")


@app.post("/api/v1/jobs", tags=["jobs"])
def create_job(body: JobRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    known_profiles = {"lakhotia", "shree", "vrindavan"}
    profiles = sorted(set(body.client_profiles))
    if not profiles:
        raise HTTPException(422, "Choose at least one client profile")
    districts = sorted({district.strip() for district in body.districts if district.strip()})
    if body.ai_review_enabled:
        # This is an explicit job-level opt-in.  The worker transmits only a
        # minimal business-evidence tuple (company, sector, district, status),
        # never direct-contact fields or source rows.
        from .settings import AI_ENABLED, AI_MAX_CALLS, AI_SPEND_APPROVED
        if not (AI_ENABLED and AI_SPEND_APPROVED and AI_MAX_CALLS > 0):
            raise HTTPException(
                409,
                "AI research review requires MATRIX_AI_ENABLED=true, "
                "MATRIX_AI_SPEND_APPROVED=true, and a positive MATRIX_AI_MAX_CALLS cap; restart the server after changing them.",
            )
    with store.connect() as conn:
        dataset = conn.execute("SELECT 1 FROM datasets WHERE id=? AND tenant_id=?", (body.dataset_id, user.tenant_id)).fetchone()
        if not dataset:
            raise HTTPException(404, "Dataset not found")
        final_filter_plan = None
        schema_hash = None
        if body.filter_plan:
            final_filter_plan, schema_hash = validate_dataset_filter_plan(conn, body.dataset_id, body.filter_plan)
        custom_profiles = []
        for profile_id in profiles:
            if profile_id in known_profiles:
                continue
            profile = conn.execute(
                "SELECT id,version,name,selection_plan_json FROM client_profiles WHERE id=? AND tenant_id=? AND retired_at IS NULL ORDER BY version DESC LIMIT 1",
                (profile_id, user.tenant_id),
            ).fetchone()
            if not profile:
                raise HTTPException(422, "Unknown client profile")
            saved_plan = json.loads(profile["selection_plan_json"] or "{}")
            if not saved_plan:
                raise HTTPException(422, "Custom profiles require a saved deterministic selection plan")
            normalized_profile_plan, _ = validate_dataset_filter_plan(conn, body.dataset_id, saved_plan)
            custom_profiles.append({"id": profile["id"], "version": profile["version"], "name": profile["name"], "selection_plan": normalized_profile_plan})
        config = {
            "districts": districts,
            "client_profiles": profiles,
            "ai_review_enabled": body.ai_review_enabled,
        }
        if custom_profiles:
            config["custom_profiles"] = custom_profiles
        if final_filter_plan:
            config["filter_plan"] = final_filter_plan
            config["filter_schema_hash"] = schema_hash
        if body.audience_plan:
            if not final_filter_plan:
                raise HTTPException(422, "AI Direct jobs require an approved filter plan")
            supplied_plan = body.audience_plan.get("predicate")
            if supplied_plan != final_filter_plan:
                raise HTTPException(422, "AI Direct plan does not match the approved filter plan")
            if body.audience_plan.get("schema_fingerprint") != schema_hash:
                raise HTTPException(422, "AI Direct plan does not match this dataset schema")
            config["audience_plan"] = {
                "plan_hash": str(body.audience_plan.get("plan_hash", ""))[:128],
                "schema_fingerprint": str(body.audience_plan.get("schema_fingerprint", ""))[:128],
                "approval_status": "user_confirmed",
            }
        existing = conn.execute("SELECT * FROM jobs WHERE tenant_id=? AND idempotency_key=?", (user.tenant_id, body.idempotency_key)).fetchone()
        if existing:
            return {"job": dict(existing), "idempotent_replay": True}
        job_id = str(uuid.uuid4())
        workspace = RUNTIME_ROOT / "workspaces" / user.tenant_id / job_id
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,config_json) VALUES(?,?,?,?,?,?,?,?)",
            (job_id, user.tenant_id, body.dataset_id, body.idempotency_key, "queued", store.now(), str(workspace), json.dumps(config, sort_keys=True)),
        )
    store.audit(user.tenant_id, user.username, "job.queued", job_id, {"dataset_id": body.dataset_id, "config": config})
    return {"job_id": job_id, "status": "queued", "worker": "Secure background worker will process this job automatically."}


@app.post("/api/v1/jobs/{job_id}/execute", tags=["jobs"])
def execute_job(job_id: str, background_tasks: BackgroundTasks, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Triggers background processing of a queued job."""
    with store.connect() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        from services.worker import runner
        background_tasks.add_task(runner.run_forever, once=True)
    except Exception as exc:
        raise HTTPException(500, f"Worker task initiation failed: {exc}")
    return {"status": "execution_started", "job_id": job_id}


@app.get("/api/v1/jobs", tags=["jobs"])
def list_jobs(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        rows = conn.execute("SELECT id,dataset_id,status,created_at,started_at,completed_at,error_code,error_detail,progress_phase,progress_percent,report_json FROM jobs WHERE tenant_id=? ORDER BY created_at DESC", (user.tenant_id,)).fetchall()
        dataset_names = {row["dataset_id"]: dataset_display_name(conn, row["dataset_id"]) for row in rows}
        export_rows = conn.execute(
            "SELECT job_id,id,path FROM exports WHERE tenant_id=?",
            (user.tenant_id,),
        ).fetchall()
    export_summary: dict[str, dict[str, int]] = {}
    for export in export_rows:
        summary = export_summary.setdefault(export["job_id"], {"registered": 0, "available": 0})
        summary["registered"] += 1
        summary["available"] += int(Path(export["path"]).is_file())
    result = []
    for row in rows:
        item = dict(row)
        item["report"] = json.loads(item.pop("report_json") or "{}")
        item["dataset_name"] = dataset_names[item["dataset_id"]]
        item["export_summary"] = export_summary.get(item["id"], {"registered": 0, "available": 0})
        result.append(item)
    return {"jobs": result}


@app.get("/api/v1/jobs/{job_id}", tags=["jobs"])
def get_job(job_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
        dataset_name = dataset_display_name(conn, row["dataset_id"]) if row else ""
    if not row:
        raise HTTPException(404, "Job not found")
    item = dict(row)
    item["report"] = json.loads(item.pop("report_json") or "{}")
    item["dataset_name"] = dataset_name
    return item


@app.post("/api/v1/jobs/{job_id}/cancel", tags=["jobs"])
def cancel_job(job_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        job = conn.execute("SELECT status FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
        if not job:
            raise HTTPException(404, "Job not found")
        if job["status"] == "queued":
            conn.execute("UPDATE jobs SET status='cancelled', completed_at=?, progress_phase='cancelled' WHERE id=? AND tenant_id=?", (store.now(), job_id, user.tenant_id))
            state = "cancelled"
        elif job["status"] == "running":
            conn.execute("UPDATE jobs SET status='cancel_requested', progress_phase='cancelling' WHERE id=? AND tenant_id=?", (job_id, user.tenant_id))
            state = "cancel_requested"
        elif job["status"] in {"cancel_requested", "cancelled"}:
            state = job["status"]
        else:
            raise HTTPException(409, "Only queued or running jobs can be cancelled")
    store.audit(user.tenant_id, user.username, "job.cancel_requested", job_id, {"state": state})
    return {"job_id": job_id, "status": state}


@app.post("/api/v1/jobs/{job_id}/retry", tags=["jobs"])
def retry_job(job_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        prior = conn.execute("SELECT dataset_id,status,config_json FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
        if not prior:
            raise HTTPException(404, "Job not found")
        if prior["status"] not in {"failed", "cancelled"}:
            raise HTTPException(409, "Only failed or cancelled jobs can be retried")
        retry_id = str(uuid.uuid4())
        workspace = RUNTIME_ROOT / "workspaces" / user.tenant_id / retry_id
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,config_json) VALUES(?,?,?,?,?,?,?,?)",
            (retry_id, user.tenant_id, prior["dataset_id"], f"retry:{job_id}:{retry_id}", "queued", store.now(), str(workspace), prior["config_json"]),
        )
    store.audit(user.tenant_id, user.username, "job.retried", retry_id, {"previous_job_id": job_id})
    return {"job_id": retry_id, "status": "queued", "retry_of": job_id}


@app.get("/api/v1/jobs/{job_id}/results", tags=["results"])
def results(job_id: str, user: Annotated[User, Depends(current_user)], offset: int = 0, limit: int = 50, search: str = "", geo_status: str = "", geo_statuses: Annotated[list[str], Query()] = [], districts: Annotated[list[str], Query()] = [], client_profiles: Annotated[list[str], Query()] = [], advanced_filters: str = "") -> dict[str, Any]:
    limit = max(1, min(limit, 200))
    with store.connect() as conn:
        job = conn.execute("SELECT workspace_path,status,dataset_id,config_json FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
        source_headers = imported_headers(conn, job["dataset_id"]) if job else []
    if not job:
        raise HTTPException(404, "Job not found")
    source = Path(job["workspace_path"]) / "all_records.csv"
    if not source.exists():
        return {"rows": [], "total": 0, "status": job["status"]}
    with source.open("r", encoding="utf-8", newline="") as handle:
        result_headers = set(next(csv.reader(handle), []))
    clauses, params = [], []
    if search:
        clauses.append("(name ILIKE ? OR company ILIKE ? OR city ILIKE ? OR email_normalized ILIKE ?)")
        params.extend([f"%{search}%"] * 4)
    known_geo = {"WB_CONFIRMED", "WB_POSSIBLE", "OUTSIDE_WB", "GEO_UNKNOWN", "REVIEW_REQUIRED"}
    selected_geo = [value for value in [geo_status, *geo_statuses] if value in known_geo]
    if selected_geo:
        clauses.append("geo_status IN (" + ",".join("?" for _ in selected_geo) + ")")
        params.extend(selected_geo)
    if districts:
        clauses.append("district IN (" + ",".join("?" for _ in districts) + ")")
        params.extend(districts)
    column_by_profile = {"lakhotia": "lakhotia_class", "shree": "shree_class", "vrindavan": "vrindavan_class"}
    selected_profiles = [column_by_profile[value] for value in client_profiles if value in column_by_profile]
    if selected_profiles:
        clauses.append("(" + " OR ".join(f"{column} IN ('Q1','Q2','P1','P2')" for column in selected_profiles) + ")")
    parsed_advanced_filters = parse_advanced_filters(advanced_filters, source_headers)
    if any(item["field"] in FILTERABLE_RESULT_FIELDS and item["field"] not in result_headers for item in parsed_advanced_filters):
        raise HTTPException(422, "This processed job does not contain one or more selected filter fields")
    advanced_clauses, advanced_params = advanced_filter_sql(parsed_advanced_filters)
    clauses.extend(advanced_clauses)
    params.extend(advanced_params)
    saved_filter_plan = json.loads(job["config_json"] or "{}").get("filter_plan")
    if saved_filter_plan:
        saved_clause, saved_params = filter_plan_sql(saved_filter_plan, result_headers)
        clauses.append(saved_clause)
        params.extend(saved_params)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    escaped = str(source).replace("'", "''")
    with duckdb.connect(":memory:") as conn:
        total = conn.execute(f"SELECT count(*) FROM read_csv_auto('{escaped}', all_varchar=true){where}", params).fetchone()[0]
        cursor = conn.execute(f"SELECT * FROM read_csv_auto('{escaped}', all_varchar=true){where} LIMIT ? OFFSET ?", [*params, limit, max(offset, 0)])
        columns = [description[0] for description in cursor.description]
        rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
    return {"rows": rows, "total": total, "offset": offset, "limit": limit, "status": job["status"]}


@app.get("/api/v1/jobs/{job_id}/filter-metadata", tags=["results"])
def filter_metadata(job_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    """Build full-job, bounded filter metadata after the engine has read a dataset.

    Direct contact/location columns are never enumerated.  For a bounded set
    of low-cardinality business attributes, values are calculated from all
    processed rows so the console can offer real filter choices rather than
    guessing from a preview.  High-cardinality fields stay free-text filters.
    """
    with store.connect() as conn:
        job = conn.execute("SELECT workspace_path,dataset_id,status FROM jobs WHERE id=? AND tenant_id=?", (job_id, user.tenant_id)).fetchone()
        source_headers = imported_headers(conn, job["dataset_id"]) if job else []
    if not job:
        raise HTTPException(404, "Job not found")
    source = Path(job["workspace_path"]) / "all_records.csv"
    supported = [{"id": key, **details, "available_records": 0} for key, details in FILTERABLE_RESULT_FIELDS.items()]
    imported_profiles: list[dict[str, Any]] = []
    if source.exists():
        with source.open("r", encoding="utf-8", newline="") as handle:
            result_headers = set((csv.reader(handle).__next__() if source.stat().st_size else []))
        available_columns = [field for field in FILTERABLE_RESULT_FIELDS if field in result_headers]
        if not available_columns:
            return {"status": job["status"], "operators": sorted(ADVANCED_FILTER_OPERATORS), "fields": supported, "imported_fields": source_headers, "vehicle_notice": "Vehicle fields are observed source attributes only. They do not establish residence, wealth, purchase intent, consent, or eligibility."}
        escaped = str(source).replace("'", "''")
        expressions = [f"count(*) FILTER (WHERE coalesce({field}, '') <> '') AS {field}" for field in available_columns]
        with duckdb.connect(":memory:") as conn:
            row = conn.execute(f"SELECT count(*) AS total_records,{','.join(expressions)} FROM read_csv_auto('{escaped}', all_varchar=true)").fetchone()
        counts = dict(zip(["total_records", *available_columns], row))
        for item in supported:
            item["available_records"] = int(counts.get(item["id"], 0) or 0)
        # `original_fields` contains source values.  Only low-cardinality,
        # non-contact business fields are enumerated; no names, phones,
        # emails, addresses, PINs, cities, states or districts are returned.
        candidates = [
            item for item in build_catalog(source_headers)
            if not bool(item["fixed"]) and item["kind"] == "categorical"
        ][:MAX_PROFILED_IMPORT_FIELDS]
        if candidates:
            with duckdb.connect(":memory:") as conn:
                conn.execute("SET memory_limit='128MB'")
                for item in candidates:
                    header = str(item["header"])
                    escaped_header = header.replace("\\", "\\\\").replace('"', '\\"')
                    json_path = f'$."{escaped_header}"'.replace("'", "''")
                    expression = f"nullif(trim(json_extract_string(original_fields, '{json_path}')), '')"
                    distinct_count = int(conn.execute(
                        f"SELECT coalesce(approx_count_distinct({expression}), 0) FROM read_csv_auto('{escaped}', all_varchar=true)"
                    ).fetchone()[0] or 0)
                    profile: dict[str, Any] = {"header": header, "group": item["group"], "distinct_count": distinct_count, "values": []}
                    if distinct_count and distinct_count <= MAX_OPTION_CARDINALITY:
                        rows = conn.execute(
                            f"SELECT {expression} AS value, count(*) AS records FROM read_csv_auto('{escaped}', all_varchar=true) "
                            f"WHERE {expression} IS NOT NULL GROUP BY 1 ORDER BY records DESC, value LIMIT ?",
                            [MAX_FILTER_VALUE_OPTIONS],
                        ).fetchall()
                        profile["values"] = [{"value": str(value), "records": int(records)} for value, records in rows]
                    imported_profiles.append(profile)
    return {
        "status": job["status"],
        "operators": ["contains", "not_contains", "is_any_of", "is_none_of", "is_present", "is_empty"],
        "fields": supported,
        "imported_fields": source_headers,
        "imported_field_profiles": imported_profiles,
        "profiling_scope": "Full processed dataset. Contact and location values are never enumerated; high-cardinality business fields remain free-text filters.",
        "vehicle_notice": "Vehicle fields are observed source attributes only. They do not establish residence, wealth, purchase intent, consent, or eligibility.",
    }


@app.get("/api/v1/jobs/{job_id}/exports", tags=["exports"])
def list_exports(job_id: str, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        job = conn.execute(
            "SELECT dataset_id,status,completed_at,config_json,report_json FROM jobs WHERE id=? AND tenant_id=?",
            (job_id, user.tenant_id),
        ).fetchone()
        rows = conn.execute("SELECT id,name,size_bytes,sha256,created_at,content_type,path FROM exports WHERE job_id=? AND tenant_id=? ORDER BY name", (job_id, user.tenant_id)).fetchall()
        dataset_name = dataset_display_name(conn, job["dataset_id"]) if job else ""
    if not job:
        raise HTTPException(404, "Job not found")
    config = json.loads(job["config_json"] or "{}")
    report = json.loads(job["report_json"] or "{}")
    exports = []
    for row in rows:
        item = dict(row)
        item["available"] = Path(item.pop("path")).is_file()
        exports.append(item)
    return {
        "exports": exports,
        "dataset_name": report.get("dataset_name") or dataset_name,
        "status": job["status"],
        "completed_at": job["completed_at"],
        "filters": report.get("export_filters") or {"client_profiles": config.get("client_profiles", []), "districts": config.get("districts", [])},
    }


@app.get("/api/v1/jobs/{job_id}/log/download", tags=["jobs"])
def download_job_log(job_id: str, user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    """Download job metadata and audit events without exporting any source records."""
    with store.connect() as conn:
        job = conn.execute(
            "SELECT id,dataset_id,status,created_at,started_at,completed_at,error_code,error_detail,progress_phase,progress_percent,report_json,config_json FROM jobs WHERE id=? AND tenant_id=?",
            (job_id, user.tenant_id),
        ).fetchone()
        events = conn.execute(
            "SELECT actor,action,created_at,details_json FROM audit_events WHERE tenant_id=? AND entity_id=? ORDER BY id",
            (user.tenant_id, job_id),
        ).fetchall()
        dataset_name = dataset_display_name(conn, job["dataset_id"]) if job else ""
    if not job:
        raise HTTPException(404, "Job not found")
    payload = dict(job)
    payload["dataset_name"] = dataset_name
    payload["report"] = json.loads(payload.pop("report_json") or "{}")
    payload["configuration"] = json.loads(payload.pop("config_json") or "{}")
    payload["events"] = []
    for event in events:
        item = dict(event)
        item["details"] = json.loads(item.pop("details_json") or "{}")
        payload["events"].append(item)
    return JSONResponse(
        {"log_version": "matrix360-job-log-v1", "job": payload},
        headers={"Content-Disposition": f'attachment; filename="matrix360-job-{job_id[:8]}-log.json"'},
    )


@app.get("/api/v1/exports/{export_id}/download", tags=["exports"])
def download_export(export_id: str, user: Annotated[User, Depends(current_user)]) -> FileResponse:
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM exports WHERE id=? AND tenant_id=?", (export_id, user.tenant_id)).fetchone()
    if not row or not Path(row["path"]).is_file():
        raise HTTPException(404, "Export not found")
    store.audit(user.tenant_id, user.username, "export.downloaded", export_id)
    return FileResponse(row["path"], media_type=row["content_type"], filename=row["name"])


@app.get("/api/v1/audit", tags=["audit"])
def audit_log(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    with store.connect() as conn:
        rows = conn.execute("SELECT actor,action,entity_id,created_at,details_json FROM audit_events WHERE tenant_id=? ORDER BY id DESC LIMIT 100", (user.tenant_id,)).fetchall()
    return {"events": [dict(row) for row in rows]}


@app.get("/api/v1/audit/download", tags=["audit"])
def download_audit_log(user: Annotated[User, Depends(current_user)]) -> JSONResponse:
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT actor,action,entity_id,created_at,details_json FROM audit_events WHERE tenant_id=? ORDER BY id DESC LIMIT 1000",
            (user.tenant_id,),
        ).fetchall()
    events = []
    for row in rows:
        event = dict(row)
        event["details"] = json.loads(event.pop("details_json") or "{}")
        events.append(event)
    return JSONResponse(
        {"log_version": "matrix360-audit-log-v1", "events": events},
        headers={"Content-Disposition": 'attachment; filename="matrix360-audit-log.json"'},
    )



@app.get("/api/v1/engine/info", tags=["v5"])
def engine_info(user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    return {
        "version": "5.0.0",
        "engine_mode": "matrix-engine-v5-agentic-dual-drive",
        "capabilities": [
            "semantic_alias_agent",
            "agentic_company_qualifier",
            "dual_drive_pipeline",
            "avinash_gateway_v1",
        ],
        "tenant_id": user.tenant_id,
    }


@app.post("/api/v1/v5/schema/resolve", tags=["v5"])
def v5_resolve_schema(body: V5SchemaResolveRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    try:
        from engine_v5.semantic_alias_agent import SemanticAliasAgent
    except ImportError:
        from matrix_engine.engine_v5.semantic_alias_agent import SemanticAliasAgent
    learned_store = RUNTIME_ROOT / "learned_aliases.json"
    agent = SemanticAliasAgent(learned_store_path=learned_store)
    if body.learn and "canonical" in body.learn and "raw" in body.learn:
        agent.learn_alias(body.learn["canonical"], body.learn["raw"])
    return agent.map_dataset_headers(body.headers, body.sample_rows)


@app.post("/api/v1/v5/filters/company", tags=["v5"])
def v5_generate_company_filters(body: V5CompanyFilterRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    try:
        from engine_v5.agentic_company_qualifier import generate_multichoice_company_filters
    except ImportError:
        from matrix_engine.engine_v5.agentic_company_qualifier import generate_multichoice_company_filters
    return generate_multichoice_company_filters(body.prompt, body.profile)


@app.post("/api/v1/v5/qualify/lead", tags=["v5"])
def v5_qualify_lead(body: V5QualifyLeadRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    try:
        from engine_v5.agentic_company_qualifier import qualify_and_score_lead
    except ImportError:
        from matrix_engine.engine_v5.agentic_company_qualifier import qualify_and_score_lead
    return qualify_and_score_lead(body.row, body.client_profile, body.reasoning_mode)


@app.post("/api/v1/v5/dual-drive/manifest", tags=["v5"])
def v5_dual_drive_manifest(body: V5DualDriveManifestRequest, user: Annotated[User, Depends(current_user)]) -> dict[str, Any]:
    try:
        from engine_v5.dual_drive_pipeline import DualDriveCloudBridge
    except ImportError:
        from matrix_engine.engine_v5.dual_drive_pipeline import DualDriveCloudBridge
    bridge = DualDriveCloudBridge(body.input_folder_url_or_id, body.output_folder_url_or_id)
    return bridge.build_sync_manifest(body.client_profiles, body.job_id, body.counts)


@app.post("/api/v1/handoff", tags=["crm"])
@app.post("/api/v1/handoff/prepare", tags=["crm"])
def crm_handoff(
    body: CRMHandoffRequest,
    user: Annotated[User, Depends(current_user)],
) -> dict[str, Any]:
    """Authenticated audience handoff package endpoint (Director P0 Clarification - HANDOFF-16).
    
    Prepares, validates, and hashes an audience snapshot package for future CRM import.
    Does NOT claim active delivery to Avinash CRM (external delivery is deferred until Avinash readiness).
    """
    verify_tenant_access(user, body.client_id)
    raw_bytes = json.dumps(body.leads, sort_keys=True).encode("utf-8")
    idempotency_hash = hashlib.sha256(raw_bytes).hexdigest()

    store.audit(
        tenant_id=user.tenant_id,
        actor=user.username,
        action="crm.handoff_prepared",
        entity_id=body.client_id,
        details={
            "lead_count": len(body.leads),
            "handoff_target": body.handoff_target,
            "snapshot_version": body.snapshot_version,
            "idempotency_hash": idempotency_hash,
            "crm_stage": "CRM_IMPORT_DEFERRED",
        },
    )

    return {
        "status": "ready_for_handoff",
        "client_id": body.client_id,
        "record_count": len(body.leads),
        "crm_stage": "CRM_IMPORT_DEFERRED",
        "external_receiver_connected": False,
        "snapshot_version": body.snapshot_version,
        "idempotency_hash": idempotency_hash,
        "manifest_checksum": idempotency_hash,
        "export_artifact_ready": True,
        "message": "Audience snapshot package prepared and cryptographically verified. Live CRM import is deferred pending external receiver availability.",
    }


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")

