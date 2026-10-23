"""Matrix 360 V5 — Zero-Hardcode Semantic Schema & Alias Resolution Agent
(Hardened against 50-Persona Red-Team Priority Collisions, BOMs, Punctuation & 30+ Aliases).
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CANONICAL_ONTOLOGY: dict[str, list[str]] = {
    "phone": [
        "phone", "mobile", "mobile no", "phone no", "contact number", "whatsapp",
        "whatsapp 91", "whatsapp normalized", "whatsapp number", "cell", "cellphone",
        "telephone", "tel", "primary phone", "direct number", "karta mobile",
        "owner mobile", "sampark", "contact person mobile", "person mobile", "mobile 1",
    ],
    "email": [
        "email", "email id", "email address", "e-mail", "mail", "official email",
        "work email", "personal email", "corporate email", "contact email", "contact person email",
    ],
    "annual_turnover": [
        "annual turnover", "turnover", "revenue", "annual revenue", "gross revenue",
        "sales turnover", "company turnover", "topline", "gross receipts", "yearly sales",
        "business volume", "fy turnover", "audited turnover", "cr turnover", "revenue band",
        "financial scale", "total sales", "gross income", "company size inr", "vyapar aay",
        "turnover in rs cr", "turnover inr", "audited topline",
    ],
    "personal_income": [
        "income", "personal income", "annual income", "monthly income", "salary", "ctc",
        "package", "net worth", "estimated net worth", "wealth band", "affluence score",
        "itr amount", "declared income", "declared itr", "household income", "earning", "aay",
        "investment capacity", "liquid assets", "hni tier", "financial capacity", "net worth wealth band",
    ],
    "budget": [
        "budget", "budget range", "property budget", "investment budget", "ticket size",
        "max budget", "spending capacity", "capital allocation", "capex budget",
        "expected price", "deal size", "purchasing power", "affordability",
    ],
    "vehicle_registration": [
        "reg no", "registration number", "vehicle no", "vehicle registration", "vahan no",
        "car number", "license plate", "number plate", "rto reg", "rc number", "chassis reg",
    ],
    "vehicle_make": [
        "vehicle make", "car make", "vehicle brand", "car brand", "auto make",
        "oem", "brand of car", "four wheeler brand", "vahan make", "automobile brand",
    ],
    "vehicle_model": [
        "vehicle model", "car model", "model name", "vehicle description", "car owned",
        "cars owned", "automobile model", "vahan model", "vahan owned", "suv model",
        "luxury car", "fleet model", "primary vehicle", "garage cars", "garage vehicles",
        "vehicles owned", "car details", "car four wheeler owned", "four wheeler garage",
    ],
    "vehicle_value": [
        "vehicle value", "car price", "ex showroom price", "idv", "insured declared value",
        "car cost", "garage value", "automobile valuation", "asset value car", "on road price",
    ],
    "luxury_assets": [
        "assets", "luxury assets", "costly items", "high value assets", "real estate owned",
        "properties owned", "club membership", "watches", "yacht", "commercial plots",
        "fleet count", "machinery value", "land bank", "portfolio value", "lifestyle indicators",
        "luxury portfolio assets", "plant or warehouse address",
    ],
    "postal_code": [
        "pin", "pincode", "pin code", "postal code", "zipcode", "zip", "area pin",
    ],
    "city": [
        "city", "business city", "town", "municipality", "location city", "tehsil",
        "taluka", "suburb", "locality", "shahar", "factory location city", "plant city",
    ],
    "district": [
        "district", "district name", "zilla", "jila", "revenue district", "zila",
        "bhoomi zila", "catchment district",
    ],
    "state": [
        "state", "state name", "province", "region", "prant", "ut", "state code", "state ut",
    ],
    "address": [
        "address", "address1", "address2", "address3", "address4", "address5",
        "street address", "registered address", "office address", "factory address",
        "residential address", "correspondence address", "full address", "pata",
    ],
    "job_title": [
        "job title", "designation", "title", "role", "position", "post", "seniority",
        "rank", "cadre", "function", "responsibility", "occupation", "profession",
        "work profile", "current role", "executive title", "officer level", "designation level",
        "cxo status", "board role", "pad", "ohda", "executive pad",
    ],
    "sector": [
        "industry", "industry type", "sector", "business sector", "business sector hint",
        "source sector hint", "industry segment", "sub industry segment", "nature of business",
        "vertical", "domain", "line of business", "lob", "business category", "category",
        "activity", "principal activity", "nic description", "msme activity", "trade category",
        "core business", "operations type", "manufacturing type", "segment", "niche",
        "principal nic activity",
    ],
    "company": [
        "company", "company name", "business name", "organisation", "organization",
        "name of the company", "legal name", "trade name", "firm", "firm name",
        "enterprise", "enterprise name", "establishment", "m/s", "ms", "agency",
        "corporate name", "account name", "employer", "employer name", "vendor name",
        "entity name", "registered entity", "brand name", "institution", "unit name",
        "factory name", "mill name", "works", "concern", "vyapar", "sanstha",
        "company firm legal title", "corporate entity",
    ],
    "name": [
        "name", "full name", "contact name", "person name", "customer name", "client name",
        "owner", "owner name", "proprietor", "proprietor name", "director name", "partner name",
        "karta", "promoter", "promoter name", "signatory", "authorized signatory", "applicant",
        "applicant name", "beneficiary", "party name", "lead name", "primary contact",
        "contact person", "key person", "decision maker", "individual name", "buyer name",
        "investor name", "member name", "registered owner", "naam", "vyakti",
        "customer full name", "karta full naam", "party full title",
    ],
}

# High-specificity priority rules so "Contact Person Mobile_1" maps to `phone` (not `name`)
# and "Factory / Plant Location City" maps to `city` (not `luxury_assets`).
PRIORITY_TOKEN_OVERRIDES: list[tuple[set[str], str]] = [
    ({"mobile", "phone", "whatsapp", "cell", "telephone", "tel", "sampark"}, "phone"),
    ({"email", "mail"}, "email"),
    ({"company", "firm", "vyapar", "enterprise", "sanstha", "establishment", "karkhana", "mill", "concern"}, "company"),
    ({"pincode", "postal", "zipcode", "zip"}, "postal_code"),
    ({"turnover", "revenue", "topline", "receipts"}, "annual_turnover"),
    ({"income", "salary", "ctc", "itr", "wealth", "networth"}, "personal_income"),
    ({"vehicle", "car", "vahan", "suv", "wheeler", "garage", "fleet"}, "vehicle_model"),
    ({"city", "town", "tehsil", "shahar", "municipality"}, "city"),
    ({"district", "zilla", "zila", "jila"}, "district"),
    ({"state", "province", "prant"}, "state"),
    ({"designation", "role", "ohda", "seniority", "position"}, "job_title"),
    ({"industry", "sector", "vertical", "nic", "segment"}, "sector"),
]


@dataclass
class ColumnMappingResult:
    raw_header: str
    canonical_field: str
    confidence: float
    method: str
    explanation: str


def normalize_token_string(text: str) -> str:
    cleaned = str(text or "").lstrip("\ufeff")
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    s = re.sub(r"[^a-zA-Z0-9]+", " ", s).lower().strip()
    return re.sub(r"\s+", " ", s)


def fingerprint_values(sample_values: list[str]) -> tuple[str | None, float, str]:
    non_empty = [str(v).strip() for v in sample_values if v is not None and str(v).strip()][:50]
    if not non_empty:
        return None, 0.0, "No non-empty sample values"

    total = len(non_empty)
    email_hits = sum(1 for v in non_empty if re.fullmatch(r"[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}", v))
    if email_hits / total >= 0.6:
        return "email", 0.96, f"{email_hits}/{total} values match email pattern"

    phone_hits = sum(
        1 for v in non_empty
        if re.fullmatch(r"(?:\+?91[\s-]?)?[6-9]\d{9}", re.sub(r"[\s().-]", "", v))
    )
    if phone_hits / total >= 0.6:
        return "phone", 0.95, f"{phone_hits}/{total} values match 10-digit Indian mobile pattern"

    pin_hits = sum(1 for v in non_empty if re.fullmatch(r"[1-8]\d{5}", v))
    if pin_hits / total >= 0.7:
        return "postal_code", 0.90, f"{pin_hits}/{total} values match 6-digit Indian PIN code"

    vahan_hits = sum(
        1 for v in non_empty
        if re.fullmatch(r"[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}", v.upper())
    )
    if vahan_hits / total >= 0.5:
        return "vehicle_registration", 0.94, f"{vahan_hits}/{total} values match RTO vehicle registration plate"

    currency_hits = sum(
        1 for v in non_empty
        if re.search(r"(?:₹|\brs\.?\b|\binr\b|\bcrore|\bcr\b|\blakh|\blac\b)", v.lower())
    )
    if currency_hits / total >= 0.5:
        return "annual_turnover", 0.82, f"{currency_hits}/{total} values contain Indian currency/Crore/Lakh units"

    return None, 0.0, ""


class SemanticAliasAgent:
    """Resolves arbitrary CSV headers (30+ aliases per field) with priority disambiguation."""

    def __init__(self, learned_store_path: Path | None = None) -> None:
        self.learned_store_path = learned_store_path
        self.ontology: dict[str, set[str]] = {
            canon: {normalize_token_string(a) for a in aliases}
            for canon, aliases in CANONICAL_ONTOLOGY.items()
        }
        if learned_store_path and learned_store_path.exists():
            try:
                learned = json.loads(learned_store_path.read_text(encoding="utf-8"))
                for canon, aliases in learned.items():
                    self.ontology.setdefault(canon, set()).update(
                        normalize_token_string(a) for a in aliases
                    )
            except Exception:
                pass

    def learn_alias(self, canonical_field: str, raw_alias: str) -> None:
        norm = normalize_token_string(raw_alias)
        self.ontology.setdefault(canonical_field, set()).add(norm)
        if self.learned_store_path:
            try:
                learned = {}
                if self.learned_store_path.exists():
                    learned = json.loads(self.learned_store_path.read_text(encoding="utf-8"))
                learned.setdefault(canonical_field, []).append(raw_alias)
                self.learned_store_path.write_text(json.dumps(learned, indent=2), encoding="utf-8")
            except Exception:
                pass

    def resolve_header(self, raw_header: str, sample_values: list[str] | None = None) -> ColumnMappingResult:
        norm = normalize_token_string(raw_header)
        if not norm:
            return ColumnMappingResult(raw_header=raw_header, canonical_field="custom_attribute", confidence=0.0, method="empty_header", explanation="Empty column header")
        compact = norm.replace(" ", "")
        header_tokens = set(norm.split())

        # 1. Exact or compact match against ontology
        for canon, aliases in self.ontology.items():
            if norm in aliases or compact in {a.replace(" ", "") for a in aliases}:
                return ColumnMappingResult(
                    raw_header=raw_header,
                    canonical_field=canon,
                    confidence=0.99,
                    method="exact_alias",
                    explanation=f"Matched known alias '{norm}' -> '{canon}'",
                )

        # 2. High-specificity token priority override (prevents 'Contact Person Mobile_1' -> 'name')
        for priority_tokens, target_canon in PRIORITY_TOKEN_OVERRIDES:
            hit = header_tokens & priority_tokens
            if hit:
                # Special check: if header has both 'company' and 'name' (and no mobile/phone/email), it's 'company'
                return ColumnMappingResult(
                    raw_header=raw_header,
                    canonical_field=target_canon,
                    confidence=0.93,
                    method="priority_token",
                    explanation=f"Priority domain token {sorted(hit)} resolved to '{target_canon}'",
                )

        if header_tokens & {"company", "firm", "organisation", "organization", "business", "enterprise", "sanstha", "establishment"}:
            return ColumnMappingResult(
                raw_header=raw_header,
                canonical_field="company",
                confidence=0.92,
                method="priority_token",
                explanation="Company/Entity token resolved to 'company'",
            )

        if header_tokens & {"name", "naam", "karta", "owner", "proprietor", "signatory", "applicant", "customer", "buyer", "investor"}:
            return ColumnMappingResult(
                raw_header=raw_header,
                canonical_field="name",
                confidence=0.91,
                method="priority_token",
                explanation="Person/Owner token resolved to 'name'",
            )

        # 3. Token overlap + SequenceMatcher fuzzy similarity
        best_canon = "custom_attribute"
        best_score = 0.0
        best_alias = ""

        for canon, aliases in self.ontology.items():
            for alias in aliases:
                alias_tokens = set(alias.split())
                overlap = len(header_tokens & alias_tokens) / max(1, len(alias_tokens))
                seq_ratio = difflib.SequenceMatcher(None, norm, alias).ratio()
                score = (0.55 * overlap) + (0.45 * seq_ratio)
                if score > best_score:
                    best_score = score
                    best_canon = canon
                    best_alias = alias

        if best_score >= 0.68:
            return ColumnMappingResult(
                raw_header=raw_header,
                canonical_field=best_canon,
                confidence=round(min(0.94, best_score), 2),
                method="token_fuzzy",
                explanation=f"Fuzzy semantic match ({int(best_score*100)}%) to '{best_alias}' -> '{best_canon}'",
            )

        # 4. Value pattern fingerprinting fallback
        if sample_values:
            fp_canon, fp_conf, fp_reason = fingerprint_values(sample_values)
            if fp_canon and fp_conf >= 0.80:
                return ColumnMappingResult(
                    raw_header=raw_header,
                    canonical_field=fp_canon,
                    confidence=fp_conf,
                    method="value_fingerprint",
                    explanation=fp_reason,
                )

        return ColumnMappingResult(
            raw_header=raw_header,
            canonical_field="custom_attribute",
            confidence=round(best_score, 2),
            method="preserved_custom",
            explanation="Preserved as dynamic filterable business attribute in original_fields",
        )

    def map_dataset_headers(
        self, headers: list[str], sample_rows: list[list[Any]] | None = None
    ) -> dict[str, Any]:
        mappings: list[ColumnMappingResult] = []
        canonical_index_map: dict[str, list[int]] = {}
        for idx, header in enumerate(headers):
            samples = [row[idx] for row in (sample_rows or []) if idx < len(row)]
            res = self.resolve_header(header, samples)
            mappings.append(res)
            if res.canonical_field != "custom_attribute":
                canonical_index_map.setdefault(res.canonical_field, []).append(idx)
        return {
            "canonical_index_map": canonical_index_map,
            "detailed_mappings": [m.__dict__ for m in mappings],
            "unmapped_headers": [m.raw_header for m in mappings if m.canonical_field == "custom_attribute"],
        }
