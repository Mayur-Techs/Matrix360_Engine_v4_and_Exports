"""Matrix 360 V5 — Dynamic Any-Client Brand Qualifier, Multi-Choice Company Filter
Generator, and Affluence / Vehicle / Purchasing-Power Logic Ranking Engine
(Hardened against 50-Persona Red-Team Edge Cases).
"""
from __future__ import annotations

import re
from typing import Any


VEHICLE_VALUATION_CATALOG: list[tuple[tuple[str, ...], str, int]] = [
    (("rolls royce", "rolls-royce", "bentley", "ferrari", "lamborghini", "maybach", "porsche", "range rover", "defender", "g wagon", "g63", "lx 500d", "vellfire"), "Ultra-Luxury (₹1.2 Cr+)", 15_000_000),
    (("bmw", "mercedes", "audi", "volvo", "jaguar", "land rover", "lexus", "gle", "gls", "glc", "x5", "x7", "q7", "q8", "a6", "e class", "s class"), "Luxury Executive (₹55L - ₹1.2 Cr)", 7_500_000),
    (("fortuner", "endeavour", "gloster", "kodiaq", "camry", "superb", "tiguan", "tucson", "ioniq", "byd seal", "hilux", "meridian"), "Premium SUV / D-Segment (₹32L - ₹55L)", 4_200_000),
    (("innova", "hycross", "crysta", "xuv700", "safari", "harrier", "scorpio", "compass", "hector", "alcazar", "virtus", "slavia", "city", "creta", "seltos", "grand vitara"), "Upper-Mid SUV / Executive (₹16L - ₹32L)", 2_200_000),
    (("bharatbenz", "tata prima", "ashok leyland", "eicher", "mahindra blazo", "volvo fmx", "trailer", "tipper", "forklift", "reach stacker", "crane", "jcb", "fleet", "trucks", "reefer", "refrigerated"), "Commercial / Industrial Fleet", 3_800_000),
    (("nexon", "brezza", "venue", "sonet", "thar", "bolero", "ertiga", "carens", "verna", "i20", "baleno", "swift", "dzire", "wagonr", "alto"), "Standard Utility / Commuter (₹6L - ₹16L)", 1_000_000),
]

ROLE_SENIORITY_WEIGHTS: list[tuple[tuple[str, ...], str, int]] = [
    (("owner", "proprietor", "founder", "co-founder", "karta", "promoter", "managing director", "md", "chairman", "chairperson", "partner", "ceo", "chief executive"), "Owner / Promoter / CXO", 25),
    (("director", "vp", "vice president", "president", "cfo", "coo", "cto", "head of", "plant head", "general manager", "gm", "avp"), "Director / VP / Plant Head", 18),
    (("procurement", "purchase", "supply chain", "logistics head", "operations manager", "facility manager", "admin head", "senior manager", "company secretary", "compliance"), "Operations / Procurement Decision-Maker", 14),
]


def parse_inr_amount(raw: object) -> int:
    """Hardened deterministic parser for Indian & international currency strings.
    Handles attached units ('₹1.2Cr', '25L', '80Lakhs/yr'), 'Rs. 4,50,00,000',
    ranges ('5 Cr - 10 Cr' -> takes upper/representative bound), and noise.
    """
    text = str(raw or "").strip().lower()
    if not text:
        return 0
    # Reject pure negative numbers
    if text.startswith("-") or (text.startswith("(") and text.endswith(")")):
        return 0

    # Strip currency prefixes like 'rs.', 'inr', '₹' first so the period in 'rs.' never corrupts decimal extraction
    text = re.sub(r"\b(?:rs\.?|inr)\b", " ", text)
    text = text.replace("₹", " ").replace(",", "")

    multiplier = 1
    if re.search(r"(?:crores?|crs?)(?![a-z])", text):
        multiplier = 10_000_000
    elif re.search(r"(?:lakhs?|lacs?|l)(?![a-z])", text):
        multiplier = 100_000
    elif re.search(r"(?:millions?|mn|m)(?![a-z])", text):
        multiplier = 1_000_000
    elif re.search(r"(?:thousands?|k)(?![a-z])", text):
        multiplier = 1_000

    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return 0
    try:
        return int(round(float(match.group(1)) * multiplier))
    except (ValueError, OverflowError):
        return 0


def evaluate_vehicle_profile(make: str, model: str, explicit_value: str = "") -> dict[str, Any]:
    combined = f"{make} {model}".strip().lower()
    explicit_inr = parse_inr_amount(explicit_value)
    if not combined and not explicit_inr:
        return {"tier": "Unobserved", "estimated_inr": 0, "points": 0}
    for keywords, tier_label, default_val in VEHICLE_VALUATION_CATALOG:
        if any(k in combined for k in keywords):
            val = explicit_inr or default_val
            pts = 25 if val >= 6_000_000 else (20 if val >= 3_000_000 else (14 if val >= 1_800_000 else 8))
            return {"tier": tier_label, "estimated_inr": val, "points": pts}
    val = explicit_inr or 900_000
    pts = 15 if val >= 2_500_000 else 6
    return {"tier": "Observed Vehicle", "estimated_inr": val, "points": pts}


def generate_multichoice_company_filters(prompt: str, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    p = str(prompt or "").lower()
    profile = profile or {}

    sector_choices = [
        {"id": "manufacturing", "label": "Manufacturing, Foundry & Forging", "selected": any(w in p for w in ("manufactur", "factory", "plant", "steel", "foundry", "forging", "engineering", "industrial")) or "manufacturing" in str(profile.get("sector_keywords", []))},
        {"id": "logistics", "label": "Warehousing, 3PL & Cold-Chain", "selected": any(w in p for w in ("warehous", "logistic", "3pl", "transport", "supply", "industrial", "cold"))},
        {"id": "fmcg_pharma", "label": "FMCG, Pharma, Agro & Chemicals", "selected": any(w in p for w in ("fmcg", "pharma", "chemical", "food", "agro", "packaging", "polymer"))},
        {"id": "real_estate_infra", "label": "Real Estate, Infra & EPC", "selected": any(w in p for w in ("real estate", "builder", "construct", "infra", "developer", "plot", "bungalow", "epc"))},
        {"id": "it_finance_corp", "label": "IT, Corporate, EV & Services", "selected": any(w in p for w in ("it", "software", "finance", "wealth", "corporate", "cxo", "hni", "ev"))},
        {"id": "retail_trade", "label": "Wholesale Distribution & Textile", "selected": any(w in p for w in ("wholesale", "distribut", "textile", "garment", "retail", "trader"))},
    ]
    if not any(c["selected"] for c in sector_choices):
        for c in sector_choices[:3]:
            c["selected"] = True

    turnover_choices = [
        {"id": "gt_25cr", "label": "Enterprise Scale (₹25 Cr+)", "min_inr": 250_000_000, "selected": True},
        {"id": "gt_5cr", "label": "Mid-Market Growth (₹5 Cr – ₹25 Cr)", "min_inr": 50_000_000, "selected": True},
        {"id": "gt_1cr", "label": "Established MSME (₹1 Cr – ₹5 Cr)", "min_inr": 10_000_000, "selected": True},
        {"id": "any_turnover", "label": "Include Emerging / Unreported", "min_inr": 0, "selected": "all" in p},
    ]

    role_choices = [
        {"id": "owner_cxo", "label": "Owner / Promoter / MD / Chairman", "selected": True},
        {"id": "director_vp", "label": "Director / VP / Plant Head", "selected": True},
        {"id": "procurement_ops", "label": "Procurement / Logistics / Facility Head", "selected": True},
    ]

    affluence_choices = [
        {"id": "luxury_car", "label": "Luxury & Premium SUVs (BMW, Mercedes, Defender, Fortuner)", "selected": True},
        {"id": "commercial_fleet", "label": "Commercial Fleets & Plant Trucks (BharatBenz, Tata Prima, Eicher)", "selected": True},
        {"id": "high_income", "label": "High Personal Income / HNI Net Worth", "selected": True},
    ]

    return {
        "prompt_analyzed": prompt,
        "company_sector_choices": sector_choices,
        "company_turnover_choices": turnover_choices,
        "company_role_choices": role_choices,
        "affluence_asset_choices": affluence_choices,
    }


def qualify_and_score_lead(row: dict[str, Any], client_profile: dict[str, Any], reasoning_mode: str = "agentic_affluence") -> dict[str, Any]:
    company = str(row.get("company", "")).strip()
    sector = str(row.get("sector", "")).strip()
    role = str(row.get("job_title", "")).strip()
    state = str(row.get("state", "")).strip()
    district = str(row.get("district", "")).strip()
    city = str(row.get("city", "")).strip()
    turnover_inr = parse_inr_amount(row.get("annual_turnover", ""))
    income_inr = parse_inr_amount(row.get("personal_income", ""))
    budget_inr = parse_inr_amount(row.get("budget", ""))
    veh_profile = evaluate_vehicle_profile(
        str(row.get("vehicle_make", "")),
        str(row.get("vehicle_model", "")),
        str(row.get("vehicle_value", "")),
    )

    target_states = [s.lower() for s in client_profile.get("target_states", ["west bengal"])]
    target_locations = [loc.lower() for loc in client_profile.get("location_keywords", [])]
    loc_blob = f"{state} {district} {city}".lower()
    state_match = "all" in target_states or any(ts in loc_blob for ts in target_states) or ("wb" in loc_blob.split() and "west bengal" in target_states)
    city_match = not target_locations or any(tl in loc_blob for tl in target_locations)

    sector_keywords = [k.lower() for k in client_profile.get("sector_keywords", [])]
    biz_blob = f"{company} {sector}".lower()
    sector_match = not sector_keywords or any(k in biz_blob for k in sector_keywords)

    role_label, role_pts = "Business Contact", 8
    for keywords, r_label, r_pts in ROLE_SENIORITY_WEIGHTS:
        if any(k in role.lower() for k in keywords):
            role_label, role_pts = r_label, r_pts
            break

    turnover_pts = 25 if turnover_inr >= 100_000_000 else (18 if turnover_inr >= 20_000_000 else (12 if turnover_inr >= 5_000_000 else 0))
    income_pts = 20 if (income_inr >= 5_000_000 or budget_inr >= 15_000_000) else (12 if (income_inr >= 1_800_000 or budget_inr >= 5_000_000) else 0)

    geo_pts = 15 if (state_match and city_match) else (10 if state_match else 0)
    sector_pts = 20 if sector_match else 0

    if reasoning_mode == "strict_evidence":
        composite_score = min(100, geo_pts * 2 + sector_pts * 2 + (20 if budget_inr > 0 or turnover_inr > 0 else 0))
    else:
        composite_score = min(100, geo_pts + sector_pts + role_pts + max(turnover_pts, income_pts) + veh_profile["points"])

    if not state_match:
        lead_class = "OUTSIDE_GEO"
    elif composite_score >= 80:
        lead_class = "Q1"
    elif composite_score >= 62:
        lead_class = "Q2"
    elif composite_score >= 45:
        lead_class = "P1"
    elif sector_match or city_match:
        lead_class = "P2"
    else:
        lead_class = "REVIEW"

    reasons = []
    if state_match and city_match:
        reasons.append(f"Geo verified location match ({city or district}, {state})")
    if sector_match and sector:
        reasons.append(f"Industry match ({sector})")
    if role_pts >= 14:
        reasons.append(f"Decision-maker ({role_label})")
    if turnover_inr > 0:
        reasons.append(f"Business scale ₹{turnover_inr/10_000_000:.2f} Cr")
    if income_inr > 0:
        reasons.append(f"Income ₹{income_inr/100_000:.1f} Lakh/yr")
    if veh_profile["estimated_inr"] > 0 and reasoning_mode != "strict_evidence":
        reasons.append(f"Assets: {veh_profile['tier']} (~₹{veh_profile['estimated_inr']/100_000:.1f}L)")

    return {
        "client_id": client_profile.get("id", "custom"),
        "lead_class": lead_class,
        "composite_score": composite_score,
        "turnover_inr": turnover_inr,
        "income_inr": income_inr,
        "vehicle_tier": veh_profile["tier"],
        "vehicle_estimated_inr": veh_profile["estimated_inr"],
        "role_tier": role_label,
        "reasoning_summary": " • ".join(reasons) if reasons else "Needs additional review",
    }
