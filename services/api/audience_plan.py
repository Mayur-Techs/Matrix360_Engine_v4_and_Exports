"""Safe, typed planning for the AI Direct audience workflow.

This is deliberately a schema-aware planner, not a row-level model call.  It
only turns explicit, supported objective terms into the existing filter DSL;
the engine remains the only component that reads and filters records.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any
import urllib.error
import urllib.request

from .filter_dsl import FilterContext, FilterValidationError, validate_plan
from .schema_intelligence import responses_output_text


WEST_BENGAL_DISTRICTS = {
    "alipurduar", "bankura", "birbhum", "cooch behar", "dakshin dinajpur",
    "darjeeling", "hooghly", "howrah", "jalpaiguri", "jhargram", "kalimpong",
    "kolkata", "malda", "murshidabad", "nadia", "north 24 parganas",
    "paschim bardhaman", "paschim medinipur", "purba bardhaman",
    "purba medinipur", "purulia", "south 24 parganas", "uttar dinajpur",
}
SECTOR_TERMS = {
    "manufacturing", "manufacturer", "warehousing", "warehouse", "logistics",
    "industrial", "steel", "textile", "pharma", "pharmaceutical", "retail",
    "education", "healthcare", "hospitality", "real estate", "construction",
}
MODEL_OPERATORS = {"contains", "eq", "present", "empty"}


class AIPlanningError(RuntimeError):
    """A safe, provider-agnostic failure code for model-backed planning."""


def ai_pipeline_available() -> bool:
    return os.getenv("MATRIX_AI_PIPELINE_ENABLED", "false").lower() == "true" and bool(os.getenv("OPENAI_API_KEY"))


def _contains_direct_identifier(value: str) -> bool:
    return bool(
        re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)
        or re.search(r"(?<!\d)\d[\d\s().-]{7,}\d(?!\d)", value)
    )


def _safe_text(value: object, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())[:limit]
    return "" if _contains_direct_identifier(text) else text


def _model_schema(headers: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "conditions": {
                "type": "array",
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string", "enum": headers},
                        "operator": {"type": "string", "enum": sorted(MODEL_OPERATORS)},
                        "value": {"type": ["string", "null"], "maxLength": 160},
                    },
                    "required": ["field", "operator", "value"],
                    "additionalProperties": False,
                },
            },
            "segment_explanation": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 220}},
            "unknown_conditions": {"type": "array", "maxItems": 8, "items": {"type": "string", "maxLength": 220}},
        },
        "required": ["conditions", "segment_explanation", "unknown_conditions"],
        "additionalProperties": False,
    }


def _request_model_plan(*, mode: str, model: str, objective: str, fields: list[dict[str, Any]], profile: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if _contains_direct_identifier(objective):
        raise AIPlanningError("AI_CONTEXT_REJECTED_DIRECT_IDENTIFIER")
    headers = [str(field["header"]) for field in fields]
    if not headers:
        raise AIPlanningError("AI_CONTEXT_HAS_NO_ELIGIBLE_FIELDS")
    profile_context = {
        key: _safe_text(value)
        for key, value in (profile or {}).items()
        if key in {"name", "industry", "default_objective", "audience_objective", "compliance_note"} and _safe_text(value)
    }
    for key in ("service_geography", "personas", "inclusions", "exclusions"):
        values = (profile or {}).get(key, [])
        if isinstance(values, list):
            profile_context[key] = [item for item in (_safe_text(value, 120) for value in values[:20]) if item]
    input_context = {
        "mode": mode,
        "objective": objective.strip(),
        "profile_context": profile_context if mode == "ai_direct" else None,
        "eligible_fields": [
            {"header": field["header"], "group": field.get("group"), "kind": field.get("kind"), "numeric_eligible": bool(field.get("numeric_eligible"))}
            for field in fields
        ],
    }
    payload = {
        "model": model,
        "store": False,
        "instructions": (
            "You create a conservative, review-required audience filter draft for Matrix 360. "
            "You receive no dataset rows, values, names, emails, phones, addresses, or personal identifiers. "
            "Use only the provided eligible field names. Every condition value must be an explicit, non-sensitive phrase from the objective or profile context. "
            "Use contains or eq only when a value is explicit; use present only when the objective asks for the existence of a field. "
            "Do not infer wealth, residence, intent, eligibility, consent, protected traits, or contactability. "
            "Return an empty conditions list for unsupported requests; never invent a field or source value."
        ),
        "input": json.dumps(input_context, separators=(",", ":"), ensure_ascii=False),
        "text": {"format": {"type": "json_schema", "name": "matrix360_audience_plan", "strict": True, "schema": _model_schema(headers)}},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:  # nosec B310: fixed provider URL
            result = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise AIPlanningError(f"AI_PLANNER_HTTP_{exc.code}") from None
    except OSError as exc:
        raise AIPlanningError("AI_PLANNER_NETWORK_UNAVAILABLE") from exc
    try:
        response_plan = json.loads(responses_output_text(result))
    except (KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
        raise AIPlanningError("AI_PLANNER_INVALID_RESPONSE") from exc
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    return response_plan, {
        "name": "openai-responses",
        "model": model,
        "row_data_transferred": False,
        "context_scope": "profile+objective+safe-schema" if mode == "ai_direct" else "objective+safe-schema",
        "usage": {key: int(usage[key]) for key in ("input_tokens", "output_tokens", "total_tokens") if isinstance(usage.get(key), int)},
    }


def build_model_backed_plan(
    *,
    mode: str,
    objective: str,
    fields: list[dict[str, Any]],
    context: FilterContext,
    profile: dict[str, Any] | None,
    model: str,
) -> tuple[dict[str, Any] | None, list[str], list[str], dict[str, Any]]:
    """Return a validated model plan or an explicitly labelled safe fallback."""
    headers = [str(field["header"]) for field in fields]
    fallback_draft, explanations, unknown = build_schema_plan(objective, headers, set(context.fields))
    fallback = validate_plan(fallback_draft, context) if fallback_draft else None
    if not ai_pipeline_available():
        return fallback, explanations, unknown, {"name": "deterministic-schema-planner", "model": None, "row_data_transferred": False, "context_scope": "local-schema-only", "usage": {}}
    try:
        model_result, provider = _request_model_plan(mode=mode, model=model, objective=objective, fields=fields, profile=profile)
        leaves = []
        for item in model_result.get("conditions", []):
            if not isinstance(item, dict) or item.get("operator") not in MODEL_OPERATORS:
                continue
            operator = str(item["operator"])
            value = None if operator in {"present", "empty"} else item.get("value")
            leaves.append({"field": item.get("field"), "operator": operator, "value": value})
        candidate = {"op": "all", "children": leaves} if len(leaves) > 1 else (leaves[0] if leaves else None)
        validated = validate_plan(candidate, context) if candidate else fallback
        model_explanations = [_safe_text(item, 220) for item in model_result.get("segment_explanation", [])]
        model_unknown = [_safe_text(item, 220) for item in model_result.get("unknown_conditions", [])]
        return validated, [item for item in model_explanations if item] or explanations, [item for item in model_unknown if item] or unknown, provider
    except (AIPlanningError, FilterValidationError) as exc:
        return fallback, explanations, [*unknown, f"Model planner unavailable ({str(exc)}); used the local deterministic draft."], {
            "name": "deterministic-safe-fallback",
            "model": None,
            "row_data_transferred": False,
            "context_scope": "local-schema-only",
            "usage": {},
            "fallback_reason": str(exc),
        }


def plan_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _header_for(headers: list[str], *markers: str) -> str | None:
    for header in headers:
        normalized = re.sub(r"[^a-z0-9]+", " ", header.casefold()).strip()
        if any(marker in normalized for marker in markers):
            return header
    return None


def build_schema_plan(objective: str, headers: list[str], normalized_fields: set[str]) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """Return an editable DSL draft from explicit safe objective signals only."""
    lowered = " ".join(objective.casefold().split())
    predicates: list[dict[str, Any]] = []
    explanations: list[str] = []
    unknown: list[str] = []

    # The plan is constrained to observed uploaded headers.  Normalized V4
    # result columns remain useful after processing, but cannot justify a
    # source-level suggestion when the source does not contain that evidence.
    state_field = _header_for(headers, "state", "region")
    district_field = _header_for(headers, "district")
    sector_field = _header_for(headers, "industry", "sector", "vertical", "business type")

    if "west bengal" in lowered:
        if state_field:
            predicates.append({"field": state_field, "operator": "contains", "value": "west bengal"})
            explanations.append("Observed state field contains West Bengal.")
        else:
            unknown.append("West Bengal was requested, but this dataset has no state/region field.")
    for district in sorted(WEST_BENGAL_DISTRICTS, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(district)}(?![a-z])", lowered):
            if district_field:
                predicates.append({"field": district_field, "operator": "eq", "value": district.title()})
                explanations.append(f"Observed district field equals {district.title()}.")
            else:
                unknown.append(f"{district.title()} was requested, but this dataset has no district field.")
            break
    explicit_sector = next((term for term in sorted(SECTOR_TERMS, key=len, reverse=True) if term in lowered), None)
    if explicit_sector:
        if sector_field:
            predicates.append({"field": sector_field, "operator": "contains", "value": explicit_sector})
            explanations.append(f"Observed industry/sector field contains the explicit objective term '{explicit_sector}'.")
        else:
            unknown.append(f"'{explicit_sector}' was requested, but this dataset has no industry/sector field.")

    if not predicates:
        unknown.append("No supported, explicit filter criterion could be safely derived. Add a present source field or use the visual builder.")
        return None, explanations, unknown
    return ({"op": "all", "children": predicates} if len(predicates) > 1 else predicates[0]), explanations, unknown
