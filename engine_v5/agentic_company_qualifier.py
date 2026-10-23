"""Matrix 360 V5 — Dynamic Any-Client Brand Qualifier, Multi-Choice Company Filter
Generator, and Affluence / Vehicle / Purchasing-Power Logic Ranking Engine.

Upgrades V4's hardcoded 3-client West Bengal rules (`lakhotia`, `shree`, `vrindavan`)
into a universal multi-tenant qualification & ranking engine that supports:
1. Any Client / Brand Onboarding at runtime (Industrial, Residential, Luxury Auto,
   Wealth Management, B2B SaaS, Commercial Warehousing, etc. across any state/region).
2. Prompt -> Multi-Choice Company-Based & Affluence Filter Generation:
   Translates plain-language prompts into structured multi-choice company facets
   (Sector/Vertical, Turnover Tier, Entity Type, Role/Seniority, Location) and
   affluence/asset facets (Personal Income, Vehicle Tier, Car Valuation, Assets).
3. Dual-Mode Evaluation & Fast Sorting:
   - Strict Evidence Mode (V4 Governance-Compliant: zero inferred intent/wealth)
   - Agentic Propensity & Affluence Ranking Mode (Composite 0-100 score combining
     Company Fit + Turnover Scale + Vehicle/Asset Valuation + Decision-Maker Role).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


# Built-in Automobile Valuation & Tier Knowledge Base (for instant offline valuation)
VEHICLE_VALUATION_CATALOG: list[tuple[tuple[str, ...], str, int]] = [
    (("rolls royce", "bentley", "ferrari", "lamborghini", "maybach", "porsche", "range rover", "defender", "g wagon", "lx 500d", "vellfire"), "Ultra-Luxury (₹1.2 Cr+)", 15_000_000),
    (("bmw", "mercedes", "audi", "volvo", "jaguar", "land rover", "lexus", "gle", "gls", "x5", "x7", "q7", "q8", "a6", "e class", "s class"), "Luxury Executive (₹55L - ₹1.2 Cr)", 7_500_000),
    (("fortuner", "endeavour", "gloster", "kodiaq", "camry", "superb", "tiguan", "tucson", "ioniq", "byd seal", "hilux", "meridian"), "Premium SUV / D-Segment (₹32L - ₹55L)", 4_200_000),
    (("innova", "hycross", "crysta", "xuv700", "safari", "harrier", "scorpio n", "compass", "hector", "alcazar", "virtus", "slavia", "city", "creta", "seltos", "grand vitara"), "Upper-Mid SUV / Executive (₹16L - ₹32L)", 2_200_000),
    (("bharatbenz", "tata prima", "ashok leyland", "eicher pro", "mahindra blazo", "volvo fmx", "trailer", "tipper", "forklift", "crane", "jcb", "fleet"), "Commercial / Industrial Fleet", 3_500_000),
    (("nexon", "brezza", "venue", "sonet", "thar", "bolero", "ertiga", "carens", "verna", "i20", "baleno", "swift", "dzire", "wagonr", "alto"), "Standard Utility / Commuter (₹6L - ₹16L)", 1_000_000),
]

ROLE_SENIORITY_WEIGHTS: list[tuple[tuple[str, ...], str, int]] = [
    (("owner", "proprietor", "founder", "co-founder", "karta", "promoter", "managing director", "md", "chairman", "chairperson", "partner", "ceo", "chief executive"), "Owner / Promoter / CXO", 25),
    (("director", "vp", "vice president", "president", "cfo", "coo", "cto", "head of", "plant head", "general manager", "gm", "avp"), "Director / VP / Plant Head", 18),
    (("procurement", "purchase", "supply chain", "logistics head", "operations manager", "facility manager", "admin head", "senior manager"), "Operations / Procurement Decision-Maker", 14),
]


def parse_inr_amount(raw: object) -> int:
    """Fast deterministic parser for Indian currency strings (Cr, Lakh, INR, ₹, K)."""
    text = str(raw or "").strip().lower()
    if not text:
        return 0
    multiplier = 1
    if re.search(r"\b(crores?|cr)\b", text):
        multiplier = 10_000_000
    elif re.search(r"\b(lakhs?|lacs?|lac|l)\b", text):
        multiplier = 100_000
    elif re.search(r"\b(million|mn|m)\b", text):
        multiplier = 1_000_000
    elif re.search(r"\b(thousand|k)\b", text):
        multiplier = 1_000
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned or cleaned.count(".") > 1:
        return 0
    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
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
    """Turn a simple natural-language prompt into selectable Multi-Choice Company & Logic filter groups."""
    p = prompt.lower()
    profile = profile or {}

    sector_choices = [
        {"id": "manufacturing", "label": "Manufacturing & Heavy Engineering", "selected": any(w in p for w in ("manufactur", "factory", "plant", "steel", "engineering", "industrial")) or "manufacturing" in str(profile.get("sector_keywords", []))},
        {"id": "logistics", "label": "Warehousing, 3PL & Cold-Chain Logistics", "selected": any(w in p for w in ("warehous", "logistic", "3pl", "transport", "supply", "industrial"))},
        {"id": "fmcg_pharma", "label": "FMCG, Pharma & Chemical Processing", "selected": any(w in p for w in ("fmcg", "pharma", "chemical", "food", "agro", "packaging"))},
        {"id": "real_estate_infra", "label": "Real Estate, Infrastructure & Construction", "selected": any(w in p for w in ("real estate", "builder", "construct", "infra", "developer", "plot", "bungalow"))},
        {"id": "it_finance_corp", "label": "IT, BFSI, Wealth & Corporate Services", "selected": any(w in p for w in ("it", "software", "finance", "wealth", "corporate", "cxo", "hni"))},
        {"id": "retail_trade", "label": "Wholesale Distribution, Textile & Retail", "selected": any(w in p for w in ("wholesale", "distribut", "textile", "garment", "retail", "trader"))},
    ]
    if not any(c["selected"] for c in sector_choices):
        sector_choices[0]["selected"] = True
        sector_choices[1]["selected"] = True

    turnover_choices = [
        {"id": "gt_25cr", "label": "Enterprise Scale (₹25 Cr+ Turnover)", "min_inr": 250_000_000, "selected": "25 cr" in p or "50 cr" in p or "enterprise" in p},
        {"id": "gt_5cr", "label": "Mid-Market Growth (₹5 Cr – ₹25 Cr)", "min_inr": 50_000_000, "selected": any(w in p for w in ("5 cr", "10 cr", "high turnover", "mid-market", "costlier"))},
        {"id": "gt_1cr", "label": "Established MSME (₹1 Cr – ₹5 Cr)", "min_inr": 10_000_000, "selected": any(w in p for w in ("1 cr", "crore", "msme", "industrial")) or not ("25 cr" in p or "5 cr" in p)},
        {"id": "any_turnover", "label": "Include Unreported Turnover (Review Queue)", "min_inr": 0, "selected": False},
    ]

    role_choices = [
        {"id": "owner_cxo", "label": "Promoter / Owner / Karta / MD / CEO", "selected": True},
        {"id": "director_vp", "label": "Director / VP / Plant Head / GM", "selected": True},
        {"id": "procurement_ops", "label": "Procurement / Logistics / Facility Head", "selected": any(w in p for w in ("logistic", "warehouse", "industrial", "supply"))},
    ]

    affluence_choices = [
        {"id": "luxury_car", "label": "Luxury / Premium SUV Owners (Fortuner, BMW, Mercedes, Rover ≥ ₹30L)", "selected": any(w in p for w in ("car", "suv", "luxury", "fortuner", "bmw", "mercedes", "costl", "wealth", "rich", "income"))},
        {"id": "commercial_fleet", "label": "Commercial Fleet / Heavy Machinery Owners (BharatBenz, Tata Prima, JCB)", "selected": any(w in p for w in ("fleet", "truck", "industrial", "warehouse", "manufactur"))},
        {"id": "high_income", "label": "High Personal Income / HNI Net Worth (≥ ₹35 Lakh/yr or ₹2 Cr+ Budget)", "selected": any(w in p for w in ("income", "salary", "hni", "wealth", "budget", "bungalow", "apartment", "costl"))},
    ]

    return {
        "prompt_analyzed": prompt,
        "company_sector_choices": sector_choices,
        "company_turnover_choices": turnover_choices,
        "company_role_choices": role_choices,
        "affluence_asset_choices": affluence_choices,
    }


def qualify_and_score_lead(row: dict[str, Any], client_profile: dict[str, Any], reasoning_mode: str = "agentic_affluence") -> dict[str, Any]:
    """Qualify and rank a single canonical record for any configured client brand."""
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

    # 1. Geography check (supports any state/city configured on the client profile)
    target_states = [s.lower() for s in client_profile.get("target_states", ["west bengal"])]
    target_locations = [loc.lower() for loc in client_profile.get("location_keywords", [])]
    loc_blob = f"{state} {district} {city}".lower()
    state_match = any(ts in loc_blob for ts in target_states) or ("wb" in loc_blob.split() and "west bengal" in target_states)
    city_match = not target_locations or any(tl in loc_blob for tl in target_locations)

    # 2. Company & Sector match
    sector_keywords = [k.lower() for k in client_profile.get("sector_keywords", [])]
    biz_blob = f"{company} {sector}".lower()
    sector_match = not sector_keywords or any(k in biz_blob for k in sector_keywords)

    # 3. Role seniority
    role_label, role_pts = "Standard Contact", 5
    for keywords, r_label, r_pts in ROLE_SENIORITY_WEIGHTS:
        if any(k in role.lower() for k in keywords):
            role_label, role_pts = r_label, r_pts
            break

    # 4. Turnover & Income points
    turnover_pts = 25 if turnover_inr >= 100_000_000 else (18 if turnover_inr >= 20_000_000 else (12 if turnover_inr >= 5_000_000 else 0))
    income_pts = 20 if (income_inr >= 5_000_000 or budget_inr >= 15_000_000) else (12 if (income_inr >= 1_800_000 or budget_inr >= 5_000_000) else 0)

    # 5. Composite Score & Classification
    geo_pts = 15 if (state_match and city_match) else (8 if state_match else 0)
    sector_pts = 20 if sector_match else 0

    if reasoning_mode == "strict_evidence":
        # V4 strict mode: ignores vehicle/income proxies, uses only geo + sector + explicit budget/intent
        composite_score = min(100, geo_pts * 2 + sector_pts * 2 + (20 if budget_inr > 0 else 0))
    else:
        # Agentic Affluence & Logic Mode: combines Company Scale + Role + Vehicle/Asset Valuation + Income + Geo
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
        reasons.append(f"Geo verified ({city or district}, {state})")
    if sector_match and sector:
        reasons.append(f"Company sector match ({sector})")
    if role_pts >= 14:
        reasons.append(f"Decision-maker ({role_label})")
    if turnover_inr > 0:
        reasons.append(f"Turnover ₹{turnover_inr/10_000_000:.2f} Cr")
    if income_inr > 0:
        reasons.append(f"Income ₹{income_inr/100_000:.1f} Lakh/yr")
    if veh_profile["estimated_inr"] > 0 and reasoning_mode != "strict_evidence":
        reasons.append(f"Asset proxy: {veh_profile['tier']} (~₹{veh_profile['estimated_inr']/100_000:.1f}L)")

    return {
        "client_id": client_profile.get("id", "custom"),
        "lead_class": lead_class,
        "composite_score": composite_score,
        "turnover_inr": turnover_inr,
        "income_inr": income_inr,
        "vehicle_tier": veh_profile["tier"],
        "vehicle_estimated_inr": veh_profile["estimated_inr"],
        "role_tier": role_label,
        "reasoning_summary": " • ".join(reasons) if reasons else "Insufficient positive signals",
    }
