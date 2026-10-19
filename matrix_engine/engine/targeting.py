"""Versioned, evidence-bound geography and client research classification rules."""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

VERSION = "4.1.1"
ROOT = Path(__file__).resolve().parents[2]
OUTSIDE_TERMS = r"pune|mumbai|bombay|gujarat|surat|ahmedabad|rajasthan|delhi|maharashtra|bengaluru|bangalore|chennai|hyderabad|odisha|bihar|jharkhand|uttar pradesh|tamil nadu|kerala|karnataka|telangana|assam|punjab|haryana|madhya pradesh|andhra pradesh|goa|chandigarh"
DIRECT_INTENT = r"enquir|inquir|interested|site visit|book(?:ing)?|purchase|buy(?:ing)?|apartment|flat|plot|bungalow|factory space|warehouse space"


def _hit(pattern: str, value: str) -> bool:
    return bool(re.search(r"\b(?:" + pattern + r")\b", value.lower()))


def _terms_hit(terms: list[str], value: str) -> bool:
    return any(re.search(r"\b" + re.escape(term.lower()) + r"\b", value.lower()) for term in terms)


@lru_cache
def geography_config() -> dict:
    return json.loads((ROOT / "config" / "geography" / "west_bengal.v1.json").read_text(encoding="utf-8"))


@lru_cache
def client_profile(profile: str) -> dict:
    return json.loads((ROOT / "config" / "client_profiles" / f"{profile}.json").read_text(encoding="utf-8"))


def _district_match(value: str) -> str:
    for district in geography_config()["districts"]:
        if _terms_hit(district["aliases"], value):
            return district["name"]
    return ""


def _city_district(value: str) -> str:
    for city, district in geography_config()["known_city_districts"].items():
        if _terms_hit([city], value):
            return district
    return ""


def geography_detail(state: object = "", district: object = "", city: object = "", address: object = "") -> tuple[str, str, str]:
    """Return (status, canonical_district, evidence); never guess an unknown district."""
    state, district, city, address = (str(value or "").lower().strip() for value in (state, district, city, address))
    combined = " ".join((state, district, city, address))
    district_name = _district_match(district) or _district_match(address) or _city_district(city)
    explicit_state = state in {"wb", "w.b.", "west bengal", "westbengal"} or "west bengal" in combined
    outside = _hit(OUTSIDE_TERMS, combined)
    wb_evidence = bool(district_name or explicit_state)
    if wb_evidence and outside:
        return "REVIEW_REQUIRED", district_name, "CONFLICTING_WB_AND_OUTSIDE_EVIDENCE"
    if outside:
        return "OUTSIDE_WB", "", "OUTSIDE_WB_EVIDENCE"
    if district_name:
        return "WB_CONFIRMED", district_name, "CANONICAL_DISTRICT_OR_CITY_MATCH"
    if explicit_state:
        return "WB_POSSIBLE", "", "STATE_ONLY_NO_CANONICAL_DISTRICT"
    return "GEO_UNKNOWN", "", "NO_GEO_EVIDENCE"


def geography(state: object, city: object, address: object) -> str:
    """Compatibility API retained for V4 callers."""
    return geography_detail(state, "", city, address)[0]


def phone_text(value: object) -> tuple[str, str]:
    source = str(value).strip()
    try:
        if re.fullmatch(r"\+?\d+(?:\.\d+)?[eE][+-]?\d+|\d+\.0+", source):
            decimal = Decimal(source)
            if decimal != decimal.to_integral_value():
                return "", "PHONE_NON_INTEGER"
            source = format(decimal, "f").split(".")[0]
    except InvalidOperation:
        return "", "PHONE_INVALID"
    if re.search(r"[,;|/]", source):
        return "", "PHONE_MULTIPLE_REVIEW"
    digits = re.sub(r"[\s()+-]", "", source)
    if digits.startswith("0091"):
        digits = digits[4:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return ("91" + digits, "") if re.fullmatch(r"[6-9][0-9]{9}", digits) else ("", "PHONE_INVALID")


def _class_for(profile_id: str, row: dict, geo: str) -> tuple[str, str]:
    if geo == "OUTSIDE_WB":
        return "N", "OUTSIDE_WB_EXCLUDED"
    profile = client_profile(profile_id)
    observed = " ".join(str(row.get(key, "")) for key in ("company", "sector")).lower()
    location = " ".join(str(row.get(key, "")) for key in ("city", "address", "district")).lower()
    intent = " ".join(str(row.get(key, "")) for key in ("interest", "enquiry", "budget", "timeline", "notes")).lower()
    direct_intent = _hit(DIRECT_INTENT, intent)
    budget_or_timeline = bool(str(row.get("budget", "")).strip() or str(row.get("timeline", "")).strip())
    relevance = _terms_hit(profile.get("sector_keywords", []), observed) or _terms_hit(profile.get("location_keywords", []), location)
    # Do not promote an unconfirmed location into an export.  Retaining the
    # observed profile signal in the reason code lets the director review a
    # potentially relevant business once its district can be verified.
    if geo in {"GEO_UNKNOWN", "REVIEW_REQUIRED", "WB_POSSIBLE"}:
        return (
            "REVIEW_REQUIRED",
            "GEO_REVIEW_REQUIRED_WITH_PROFILE_RELEVANCE" if relevance else "GEO_REVIEW_REQUIRED",
        )
    if direct_intent and budget_or_timeline:
        return "Q1", "DIRECT_INTENT_WITH_BUDGET_OR_TIMELINE"
    if direct_intent:
        return "Q2", "DIRECT_INTENT_NEEDS_BUDGET_OR_TIMELINE"
    if relevance:
        return "P2", "OBSERVED_PROFILE_RELEVANCE_ONLY"
    return "N", "NO_SUPPORTED_PROFILE_SIGNAL"


def classify(row: dict) -> dict:
    geo, district, geo_evidence = geography_detail(row.get("state", ""), row.get("district", ""), row.get("city", ""), row.get("address", ""))
    row["geo_status"] = geo
    row["district"] = district
    row["geo_evidence"] = geo_evidence
    reasons = {}
    for profile_id in ("lakhotia", "shree", "vrindavan"):
        value, reason = _class_for(profile_id, row, geo)
        row[f"{profile_id}_class"] = value
        reasons[profile_id] = reason
    row["reason_codes"] = json.dumps(reasons, sort_keys=True)
    row["rationale"] = "Evidence-bound research classification; no inferred consent, wealth, ownership, or buying intent."
    return row
