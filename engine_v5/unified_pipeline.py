"""Matrix 360 Unified End-to-End Pipeline:
Stage 1 (Zero-API Lead Discovery & Web Crawler)
   --> Stage 2 (V4/V5 25+ Alias Mapping, Company & Affluence Qualification Engine)
   --> Stage 3 (Self-Contained SQLite WAL Production Lead Store & Avinash CRM Handoff)

Works 100% autonomously without requiring external paid APIs (Serper, paid scrapers, or external DBs),
while supporting optional OpenAI/Gemini keys, Supabase Postgres sync, and Dual Google Drive sync.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from lead_discovery.agents import (
        ContactExtractionAgent,
        DomainDiscoveryAgent,
        PlainEnglishFilterSpec,
        PromptFilterAgent,
        QualificationAgent,
    )
    from lead_discovery.config import EngineConfig
    from lead_discovery.discovery_zero_api import (
        ArchivalIndexHarvester,
        CrtShHarvester,
        HybridScaleOrchestrator,
        KeylessSearchRotator,
        ObfuscatedContactDecoder,
        OverpassIndustrialHarvester,
        SupplyChainSnowballSpider,
    )
    from lead_discovery.integrations import CRMIntegrationHub
    from lead_discovery.scale_50k_engine import BusinessAndPersonaSynthesizer, SQLiteWALCheckpointStore
    from lead_discovery.verified_pilot_data import CSV_SHA256, PILOT_RECORDS
except ImportError:
    from agents import (
        ContactExtractionAgent,
        DomainDiscoveryAgent,
        PlainEnglishFilterSpec,
        PromptFilterAgent,
        QualificationAgent,
    )
    from config import EngineConfig
    from discovery_zero_api import (
        ArchivalIndexHarvester,
        CrtShHarvester,
        HybridScaleOrchestrator,
        KeylessSearchRotator,
        ObfuscatedContactDecoder,
        OverpassIndustrialHarvester,
        SupplyChainSnowballSpider,
    )
    from integrations import CRMIntegrationHub
    from scale_50k_engine import BusinessAndPersonaSynthesizer, SQLiteWALCheckpointStore
    from verified_pilot_data import CSV_SHA256, PILOT_RECORDS

from engine_v5.agentic_company_qualifier import qualify_and_score_lead
from engine_v5.semantic_alias_agent import SemanticAliasAgent


def infer_industrial_scale_from_evidence(record: dict[str, Any]) -> tuple[str, str]:
    """Infer realistic observable company scale & fleet/facility assets from verified crawler evidence."""
    ev = f"{record.get('facility_evidence', '')} {record.get('msme_or_cert_evidence', '')} {record.get('sector', '')}".lower()
    comp = str(record.get("company_name", "")).lower()

    # Estimate observable turnover tier from public listing / CIN / plant footprint
    if any(k in ev for k in ("listed", "miniratna", "bse:", "375k mtpa", "6.78 million", "2,000+ acres", "naphtha-based", "ultra mega")):
        turnover_str = "₹ 250 Crore"
    elif any(k in ev for k in ("plc", "50,000+ mtpa", "24,000 mtpa", "4 manufacturing plants", "3 manufacturing plants", "1.58 lakh sq. ft.", "2,500+ truck")):
        turnover_str = "₹ 65 Crore"
    elif any(k in ev for k in ("40,000+ sq. ft.", "50,000 sq. ft.", "two west bengal", "unit 1", "unit i & ii", "pvt. ltd.", "limited")):
        turnover_str = "₹ 18 Crore"
    elif "micro" in ev or "msme" in ev or "ssi" in ev:
        turnover_str = "₹ 4.5 Crore"
    else:
        turnover_str = "₹ 8 Crore"

    # Observable fleet / industrial asset indicator
    if any(k in ev for k in ("truck", "trailer", "reach stacker", "forklift", "reefer", "fleet", "tanker")):
        asset_str = "Commercial Fleet (Trailers / Reach Stackers / Reefer Trucks)"
    elif any(k in ev for k in ("warehouse", "3pl", "cold storage", "cfs", "pallet")):
        asset_str = "Grade-A 3PL Warehouse / Cold Storage Facility"
    elif any(k in ev for k in ("foundry", "forging", "rolling mill", "asu plant", "fab 1", "kiln", "furnace")):
        asset_str = "Heavy Industrial Plant & Foundry Machinery"
    else:
        asset_str = record.get("location_type", "Industrial Facility")

    return turnover_str, asset_str


def convert_crawler_record_to_v4_v5_row(
    record: dict[str, Any],
    client_profile: dict[str, Any] | None = None,
    reasoning_mode: str = "agentic_affluence",
) -> dict[str, Any]:
    """Bridge Stage 1 Crawler Record -> Stage 2 V4/V5 Canonical Qualification Record."""
    client_profile = client_profile or {
        "id": "lakhotia",
        "name": "Lakhotia Industrial Complex",
        "target_states": ["west bengal", "wb"],
        "location_keywords": ["howrah", "hooghly", "kolkata", "sankrail", "dhulagarh", "dankuni", "uluberia", "baidyabati", "taratala", "falta", "kalyani", "haldia", "durgapur"],
        "sector_keywords": ["manufacturing", "foundry", "forging", "fabrication", "warehousing", "3pl", "logistics", "cold", "packaging", "polymer", "steel", "alloy", "engineering", "valves", "pumps", "chemical", "solar", "jute", "food"],
    }

    turnover_str, asset_str = infer_industrial_scale_from_evidence(record)
    district_raw = str(record.get("catchment_district", "Howrah"))
    primary_district = district_raw.split("&")[0].split(",")[0].strip()
    is_non_wb = "non-wb" in district_raw.lower()
    state_val = "Bihar" if is_non_wb else "West Bengal"

    named_person = str(record.get("named_contact", "")).strip() or f"Management ({record.get('company_name', '')[:28]})"
    role_val = str(record.get("role", "")).strip() or ("Managing Director / Plant Head" if record.get("qualification_status") == "PREPASS" else "Regional Contact")
    phone_val = str(record.get("contact_person_phone") or record.get("company_phone") or "").split("|")[0].strip()
    email_val = str(record.get("contact_person_email") or record.get("company_email") or "").split("|")[0].strip()

    canonical_input = {
        "name": named_person,
        "company": record.get("company_name", ""),
        "job_title": role_val,
        "sector": record.get("sector", ""),
        "state": state_val,
        "district": primary_district,
        "city": primary_district,
        "annual_turnover": turnover_str,
        "personal_income": "",
        "budget": turnover_str,
        "vehicle_make": "",
        "vehicle_model": asset_str,
        "vehicle_value": "",
        "phone": phone_val,
        "email": email_val,
        "address": record.get("plant_or_warehouse_address", ""),
    }

    v5_eval = qualify_and_score_lead(canonical_input, client_profile, reasoning_mode=reasoning_mode)

    # Reconcile crawler qualification_status (PREPASS / REVIEW / EXCLUDE) with V4/V5 class
    crawler_status = str(record.get("qualification_status", "PREPASS")).upper()
    if crawler_status == "EXCLUDE":
        final_class = "N"
        final_score = min(25, v5_eval["composite_score"])
    elif crawler_status == "REVIEW":
        final_class = "P2" if v5_eval["lead_class"] in {"Q1", "Q2", "P1"} else "REVIEW_REQUIRED"
        final_score = min(74, max(52, v5_eval["composite_score"]))
    else:
        final_class = v5_eval["lead_class"]
        final_score = max(78, v5_eval["composite_score"])

    return {
        "source_id": record.get("source_id", f"CRW-{uuid.uuid4().hex[:6].upper()}"),
        "canonical_domain": record.get("canonical_domain", ""),
        "verified_source_url": record.get("verified_source_url", ""),
        "crawler_status": crawler_status,
        "crawler_confidence": record.get("confidence_score", 0.94),
        "v4_v5_class": final_class,
        "composite_score": final_score,
        "name": named_person,
        "role": role_val,
        "company_name": record.get("company_name", ""),
        "sector": record.get("sector", ""),
        "location_type": record.get("location_type", ""),
        "catchment_district": district_raw,
        "state": state_val,
        "plant_or_warehouse_address": record.get("plant_or_warehouse_address", ""),
        "head_office_address": record.get("head_office_address", ""),
        "facility_evidence": record.get("facility_evidence", ""),
        "msme_or_cert_evidence": record.get("msme_or_cert_evidence", ""),
        "company_phone": record.get("company_phone", ""),
        "company_email": record.get("company_email", ""),
        "contact_person_phone": record.get("contact_person_phone", ""),
        "contact_person_email": record.get("contact_person_email", ""),
        "estimated_turnover": turnover_str,
        "turnover_inr": v5_eval["turnover_inr"],
        "observed_assets_or_fleet": asset_str,
        "vehicle_estimated_inr": v5_eval["vehicle_estimated_inr"],
        "research_fit_reasons": record.get("research_fit_reasons", ""),
        "v5_reasoning_summary": v5_eval["reasoning_summary"],
        "pages_crawled": record.get("pages_crawled", 1),
        "extraction_method": record.get("extraction_method", "Zero-API Multi-Vector OSINT"),
    }


from contextlib import contextmanager

class ProductionLeadVault:
    """Self-contained SQLite WAL production lead store so the system runs with zero external DB dependency."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS production_leads (
                    lead_id TEXT PRIMARY KEY,
                    canonical_domain TEXT NOT NULL,
                    client_id TEXT NOT NULL DEFAULT 'lakhotia',
                    crawler_status TEXT NOT NULL,
                    v4_v5_class TEXT NOT NULL,
                    composite_score INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    named_contact TEXT,
                    role TEXT,
                    company_phone TEXT,
                    company_email TEXT,
                    contact_person_phone TEXT,
                    contact_person_email TEXT,
                    catchment_district TEXT,
                    location_type TEXT,
                    plant_or_warehouse_address TEXT,
                    head_office_address TEXT,
                    facility_evidence TEXT,
                    msme_or_cert_evidence TEXT,
                    estimated_turnover TEXT,
                    observed_assets_or_fleet TEXT,
                    verified_source_url TEXT,
                    crm_stage TEXT NOT NULL DEFAULT 'DISCOVERED_AND_QUALIFIED',
                    payload_json TEXT NOT NULL,
                    job_id TEXT,
                    source TEXT NOT NULL DEFAULT 'live_evidence_crawler',
                    lead_type TEXT NOT NULL DEFAULT 'person',
                    is_reference_seed INTEGER DEFAULT 0,
                    created_at REAL,
                    updated_at REAL NOT NULL
                );
                """
            )
            # Safe schema migration for existing SQLite files
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(production_leads)")
            existing_cols = {r[1] for r in cur.fetchall()}
            for col_def in [
                ("job_id", "TEXT"),
                ("source", "TEXT NOT NULL DEFAULT 'live_evidence_crawler'"),
                ("lead_type", "TEXT NOT NULL DEFAULT 'person'"),
                ("is_reference_seed", "INTEGER DEFAULT 0"),
                ("created_at", "REAL")
            ]:
                if col_def[0] not in existing_cols:
                    try:
                        conn.execute(f"ALTER TABLE production_leads ADD COLUMN {col_def[0]} {col_def[1]}")
                    except Exception:
                        pass

    def upsert_leads(
        self,
        leads: list[dict[str, Any]],
        client_id: str = "lakhotia",
        job_id: str | None = None,
        source: str | None = None,
        is_reference_seed: int = 0
    ) -> int:
        now_ts = time.time()
        saved = 0
        with self._connect() as conn:
            for item in leads:
                dom = str(item.get("canonical_domain") or item.get("source_id") or uuid.uuid4().hex)
                named_c = str(item.get("named_contact") or item.get("director_name") or "").strip()
                contact_suffix = f":{re.sub(r'[^a-z0-9]', '', named_c.lower())[:16]}" if named_c else ""
                lead_id = item.get("lead_id") or f"{client_id}:{dom}{contact_suffix}"
                eff_source = source or str(item.get("source") or "live_evidence_crawler")
                eff_job = job_id or item.get("job_id") or ""
                eff_type = str(item.get("lead_type") or ("person" if (item.get("named_contact") or item.get("director_name")) else "organization"))
                eff_is_seed = is_reference_seed or (1 if item.get("is_reference_seed") else 0)

                conn.execute(
                    """
                    INSERT INTO production_leads (
                        lead_id, canonical_domain, client_id, crawler_status, v4_v5_class,
                        composite_score, company_name, sector, named_contact, role,
                        company_phone, company_email, contact_person_phone, contact_person_email,
                        catchment_district, location_type, plant_or_warehouse_address,
                        head_office_address, facility_evidence, msme_or_cert_evidence,
                        estimated_turnover, observed_assets_or_fleet, verified_source_url,
                        crm_stage, payload_json, job_id, source, lead_type, is_reference_seed, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(lead_id) DO UPDATE SET
                        crawler_status=excluded.crawler_status,
                        v4_v5_class=excluded.v4_v5_class,
                        composite_score=excluded.composite_score,
                        company_name=excluded.company_name,
                        named_contact=excluded.named_contact,
                        company_phone=excluded.company_phone,
                        company_email=excluded.company_email,
                        payload_json=excluded.payload_json,
                        job_id=COALESCE(excluded.job_id, production_leads.job_id),
                        source=excluded.source,
                        lead_type=excluded.lead_type,
                        updated_at=excluded.updated_at
                    """,
                    (
                        lead_id,
                        dom,
                        client_id,
                        str(item.get("crawler_status") or item.get("qualification_status") or "PREPASS"),
                        str(item.get("v4_v5_class") or "Q1"),
                        int(item.get("composite_score") or int((item.get("confidence_score") or 0.85) * 100)),
                        str(item.get("company_name") or item.get("company") or ""),
                        str(item.get("sector") or ""),
                        str(item.get("named_contact") or item.get("director_name") or item.get("name") or ""),
                        str(item.get("role") or ""),
                        str(item.get("company_phone") or item.get("phone") or ""),
                        str(item.get("company_email") or item.get("email") or ""),
                        str(item.get("contact_person_phone") or ""),
                        str(item.get("contact_person_email") or ""),
                        str(item.get("catchment_district") or item.get("district") or ""),
                        str(item.get("location_type") or "Plant / Operating Unit"),
                        str(item.get("plant_or_warehouse_address") or item.get("address") or ""),
                        str(item.get("head_office_address") or ""),
                        str(item.get("facility_evidence") or ""),
                        str(item.get("msme_or_cert_evidence") or ""),
                        str(item.get("estimated_turnover") or ""),
                        str(item.get("observed_assets_or_fleet") or ""),
                        str(item.get("verified_source_url") or item.get("source_url") or ""),
                        str(item.get("crm_stage", "DISCOVERED_AND_QUALIFIED")),
                        json.dumps(item, ensure_ascii=False),
                        eff_job,
                        eff_source,
                        eff_type,
                        eff_is_seed,
                        now_ts,
                        now_ts,
                    ),
                )
                saved += 1
        return saved

    def list_leads(
        self,
        client_id: str | None = None,
        job_id: str | None = None,
        v4_v5_class: str | None = None,
        crawler_status: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if client_id and client_id != "ALL":
            clauses.append("client_id = ?")
            params.append(client_id)
        if job_id:
            clauses.append("job_id = ?")
            params.append(job_id)
        if v4_v5_class and v4_v5_class != "ALL":
            clauses.append("v4_v5_class = ?")
            params.append(v4_v5_class)
        if crawler_status and crawler_status != "ALL":
            clauses.append("crawler_status = ?")
            params.append(crawler_status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM production_leads{where} ORDER BY updated_at DESC, composite_score DESC LIMIT ?",
                [*params, limit],
            ).fetchall()
        
        results = []
        for r in rows:
            d = dict(r)
            # Rehydrate payload_json if available
            try:
                pj = json.loads(d.get("payload_json") or "{}")
                if isinstance(pj, dict):
                    # Merge but keep top-level DB fields authoritative
                    merged = {**pj, **d}
                    results.append(merged)
                    continue
            except Exception:
                pass
            results.append(d)
        return results

    def update_crm_stage(self, lead_id: str, crm_stage: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE production_leads SET crm_stage = ?, updated_at = ? WHERE lead_id = ?",
                (crm_stage, time.time(), lead_id),
            )
            return cur.rowcount > 0
