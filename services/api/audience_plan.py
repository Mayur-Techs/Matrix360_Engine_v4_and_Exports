"""Safe, typed planning for the AI Direct audience workflow.

This is deliberately a schema-aware planner, not a row-level model call.  It
only turns explicit, supported objective terms into the existing filter DSL;
the engine remains the only component that reads and filters records.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


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
