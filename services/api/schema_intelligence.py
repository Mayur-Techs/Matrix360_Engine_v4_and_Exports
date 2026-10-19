"""Privacy-preserving schema cataloguing for imported audience datasets.

The catalog is deterministic and local.  Its optional AI refinement sends only
non-contact *header names* to the configured provider; it never sends rows,
sample values, contact details, or inferred personal traits.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from .numeric_values import is_identifier_header, is_numeric_semantic_header


CONTACT_TERMS = ("name", "email", "mail", "phone", "mobile", "telephone", "address", "street", "pin", "postal", "zip")

GROUPS = {
    "contact": "Contact and location constants",
    "company": "Company and ownership",
    "role": "Role and organisation",
    "industry": "Industry and operating profile",
    "firmographics": "Company scale and commercial profile",
    "asset": "Observed assets and operations",
    "source": "Source and data quality",
    "custom": "Imported business attributes",
}


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def is_contact_header(header: str) -> bool:
    """Treat direct contact/location columns as fixed identifiers, not AI input."""
    value = _normalise(header)
    # Company names are business attributes, even though they contain the word
    # "name". They must remain usable as an account filter.
    if re.search(r"\b(company|organisation|organization|business|firm)\s+name\b", value) or re.search(r"\bname\s+(of|for)\s+(company|organisation|organization|business|firm)\b", value):
        return False
    return any(re.search(rf"\b{re.escape(term)}\b", value) for term in CONTACT_TERMS)


def infer_field(header: str, stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an explainable, header-only classification for one column."""
    value = _normalise(header)
    tokens = set(value.split())
    group, kind, tags = "custom", "categorical", ["imported"]
    if is_contact_header(header) or tokens & {"city", "state", "district", "country", "location", "region"}:
        group, kind, tags = "contact", "fixed", ["contact", "location"]
    elif tokens & {"company", "organisation", "organization", "business", "employer", "firm"}:
        group, kind, tags = "company", "categorical", ["company"]
    elif tokens & {"owner", "proprietor", "founder", "director", "partner", "promoter"}:
        group, kind, tags = "company", "categorical", ["ownership"]
    elif tokens & {"designation", "title", "role", "position", "seniority"}:
        group, kind, tags = "role", "categorical", ["role"]
    elif tokens & {"department", "dept", "function", "team"}:
        group, kind, tags = "role", "categorical", ["department"]
    elif tokens & {"industry", "sector", "vertical", "segment", "subindustry", "sub", "niche"}:
        group, kind, tags = "industry", "categorical", ["industry"]
    elif tokens & {"revenue", "turnover", "headcount", "employee", "employees", "staff", "size", "annual"}:
        group, kind, tags = "firmographics", "numeric", ["company scale"]
    elif tokens & {"vehicle", "car", "make", "model", "variant", "fuel", "registration", "fleet", "machinery", "asset", "plot", "area", "sqft", "warehouse", "plant"}:
        group, kind, tags = "asset", "categorical", ["observed attribute"]
    elif tokens & {"source", "sheet", "status", "flag", "quality", "date", "created", "updated"}:
        group, kind, tags = "source", "categorical", ["source"]
    numeric_stats = stats or {}
    numeric_valid = int(numeric_stats.get("numeric_valid", 0) or 0)
    numeric_invalid = int(numeric_stats.get("numeric_invalid", 0) or 0)
    numeric_eligible = is_numeric_semantic_header(header) and not is_identifier_header(header) and numeric_valid > 0
    if is_numeric_semantic_header(header) and not numeric_eligible:
        kind = "unknown"
    return {
        "header": header,
        "label": header,
        "group": GROUPS[group],
        "group_id": group,
        "kind": kind,
        "tags": tags,
        "fixed": group == "contact",
        "ai_eligible": not is_contact_header(header),
        "numeric_eligible": numeric_eligible,
        "numeric_observed": numeric_valid,
        "numeric_invalid": numeric_invalid,
        "numeric_currencies": sorted({str(value).upper() for value in numeric_stats.get("numeric_currencies", []) if str(value).strip()}),
    }


def build_catalog(headers: list[str], field_stats: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Catalogue each unique imported header in a predictable presentation order."""
    seen: set[str] = set()
    result: list[dict[str, str | bool | list[str]]] = []
    for item in headers:
        header = str(item).strip()
        key = header.casefold()
        if not header or key in seen or len(header) > 160:
            continue
        seen.add(key)
        stats = next((value for key, value in (field_stats or {}).items() if key.casefold() == header.casefold()), None)
        result.append(infer_field(header, stats))
    order = {name: position for position, name in enumerate(GROUPS)}
    return sorted(result, key=lambda item: (order.get(str(item["group_id"]), 99), str(item["label"]).casefold()))


def schema_ai_available() -> bool:
    return os.getenv("MATRIX_SCHEMA_AI_ENABLED", "true").lower() == "true" and bool(os.getenv("OPENAI_API_KEY"))


def suggest_catalog_refinements(catalog: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Ask for display-only grouping suggestions from header names alone.

    This never changes filters, classifications, exports, or deterministic
    mappings.  Callers must merge only suggestions whose headers were present
    in the original catalog.
    """
    if not schema_ai_available():
        raise RuntimeError("SCHEMA_AI_DISABLED_OR_KEY_MISSING")
    headers = [str(item["header"]) for item in catalog if item.get("ai_eligible")]
    if not headers:
        return []
    schema = {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "header": {"type": "string"},
                        "group": {"type": "string", "enum": list(GROUPS.values())},
                        "label": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["header", "group", "label", "reason"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["suggestions"],
        "additionalProperties": False,
    }
    payload = {
        "model": os.getenv("MATRIX_SCHEMA_AI_MODEL", "gpt-4o-mini"),
        "store": False,
        "instructions": (
            "You organize a B2B audience dataset's column labels. The input contains only non-contact header names, never records. "
            "Return short display labels and one of the supplied groups. Do not infer a person's wealth, interest, consent, identity, or intent. "
            "Do not invent headers and do not propose targeting or classification rules."
        ),
        "input": json.dumps({"headers": headers}, separators=(",", ":")),
        "text": {"format": {"type": "json_schema", "name": "schema_catalog", "strict": True, "schema": schema}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310: fixed provider URL
            result = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SCHEMA_AI_HTTP_{exc.code}") from None
    except OSError as exc:
        raise RuntimeError("SCHEMA_AI_NETWORK_UNAVAILABLE") from exc
    try:
        suggestions = json.loads(result.get("output_text", "{}"))["suggestions"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("SCHEMA_AI_INVALID_RESPONSE") from exc
    allowed_headers = set(headers)
    allowed_groups = set(GROUPS.values())
    safe: list[dict[str, str]] = []
    for item in suggestions:
        if not isinstance(item, dict) or item.get("header") not in allowed_headers or item.get("group") not in allowed_groups:
            continue
        label = str(item.get("label", "")).strip()[:80]
        reason = str(item.get("reason", "")).strip()[:180]
        if label and reason:
            safe.append({"header": str(item["header"]), "group": str(item["group"]), "label": label, "reason": reason})
    return safe
