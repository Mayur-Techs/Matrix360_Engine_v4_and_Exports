"""Matrix 360 & LeadScope AI Studio — FastAPI Discovery & Web Crawler Endpoints.

Provides zero-API 8-vector OSINT lead discovery, obfuscated contact decoding,
live Playwright / HTTP crawling, and direct bridge transfer to Matrix Engine V5.
"""
from __future__ import annotations
from lead_discovery.maps_adapter import RomitMapsAdapter

import csv
import hashlib
import io
import json
import os
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Ensure lead_discovery package is in path
_pkg_root = Path(__file__).resolve().parent.parent.parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

from services.api.security import User, current_user, verify_tenant_access, verify_platform_admin
from services.api import store
from services.api.settings import RUNTIME_ROOT

from lead_discovery.config import EngineConfig
from lead_discovery.agents import PromptFilterAgent
from lead_discovery.crawler import PlaywrightVisualCrawler
from lead_discovery.discovery_zero_api import (
    HybridScaleOrchestrator,
    ObfuscatedContactDecoder,
    DomainDiscoveryAgent,
    SupplyChainSnowballSpider,
    KeylessSearchRotator,
)
from lead_discovery.verified_pilot_data import PILOT_RECORDS, CSV_SHA256
from lead_discovery.scale_50k_engine import BusinessAndPersonaSynthesizer
from lead_discovery.supabase_sync import SupabaseLeadSync

router = APIRouter(tags=["lead_discovery"])

CONFIG = EngineConfig()
FILTER_AGENT = PromptFilterAgent()
SUPABASE_SYNC = SupabaseLeadSync()


class PromptRequest(BaseModel):
    prompt: str
    target_lead_count: int = 500
    target_leads: Optional[int] = None


class ApiKeyUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = ""
    gemini_api_key: Optional[str] = ""
    serper_api_key: Optional[str] = ""
    google_maps_api_key: Optional[str] = ""
    zero_api_discovery_enabled: bool = True


class CrawlRequest(BaseModel):
    url: str


class ObfuscatedHtmlRequest(BaseModel):
    raw_html: str
    source_domain: str = "example.com"


class SendToEngineRequest(BaseModel):
    dataset_name: Optional[str] = None
    leads: Optional[List[Dict[str, Any]]] = None
    filter_status: Optional[str] = "PREPASS"
    status_filter: Optional[str] = None


def _normalize_lead(r: Dict[str, Any]) -> Dict[str, Any]:
    norm = dict(r)
    norm["lead_id"] = r.get("lead_id") or ""
    norm["company"] = r.get("company_name", "") or r.get("company", "")
    norm["company_name"] = norm["company"]
    norm["district"] = r.get("catchment_district", "") or r.get("district", "")
    norm["catchment_district"] = norm["district"]
    norm["status"] = r.get("qualification_status", "") or r.get("v4_v5_class", "") or r.get("status", "REVIEW")
    norm["qualification_status"] = norm["status"]
    raw_conf = r.get("confidence_score") or r.get("confidence")
    norm["confidence"] = float(raw_conf) if raw_conf is not None else 0.50
    norm["confidence_score"] = norm["confidence"]
    norm["phone"] = r.get("company_phone", "") or r.get("contact_person_phone", "") or r.get("phone", "")
    norm["company_phone"] = norm["phone"]
    norm["email"] = r.get("company_email", "") or r.get("contact_person_email", "") or r.get("email", "")
    norm["company_email"] = norm["email"]
    norm["domain"] = r.get("canonical_domain", "") or r.get("domain", "")
    norm["canonical_domain"] = norm["domain"]
    norm["cin"] = r.get("cin", "")
    norm["director_name"] = r.get("named_contact", "") or r.get("director_name", "")
    norm["named_contact"] = norm["director_name"]
    norm["state"] = r.get("state") or ""
    norm["estimated_turnover"] = r.get("estimated_turnover") or ""
    norm["observed_assets_or_fleet"] = r.get("observed_assets_or_fleet") or ""
    return norm


@router.get("/api/health")
@router.get("/api/discovery/health")
def discovery_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "system": "LeadScope AI Studio v3.0 (Zero-API Engine)",
        "engine": "ai_lead_discovery_zero_api",
        "agentic_mode": True,
        "zero_api_discovery_enabled": CONFIG.zero_api_discovery_enabled,
        "serper_api_required": False,
        "llm_configured": CONFIG.has_llm_key(),
        "total_verified_records": len(PILOT_RECORDS),
        "eligible_domains": sum(1 for r in PILOT_RECORDS if r.get("qualification_status") in ("PREPASS", "REVIEW")),
        "csv_sha256": CSV_SHA256,
        "supabase_configured": SUPABASE_SYNC.is_configured,
    }


@router.post("/api/config-keys")
@router.post("/api/discovery/config-keys")
def update_api_keys(req: ApiKeyUpdateRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    verify_platform_admin(user)
    CONFIG.zero_api_discovery_enabled = req.zero_api_discovery_enabled
    if req.openai_api_key is not None:
        CONFIG.openai_api_key = req.openai_api_key.strip()
    if req.gemini_api_key is not None:
        CONFIG.gemini_api_key = req.gemini_api_key.strip()
    if req.serper_api_key is not None:
        CONFIG.serper_api_key = req.serper_api_key.strip()
    if req.google_maps_api_key is not None:
        CONFIG.google_maps_api_key = req.google_maps_api_key.strip()
    return {
        "status": "updated",
        "zero_api_discovery_enabled": CONFIG.zero_api_discovery_enabled,
        "openai_configured": bool(CONFIG.openai_api_key),
        "gemini_configured": bool(CONFIG.gemini_api_key),
        "serper_configured": bool(CONFIG.serper_api_key),
        "google_maps_configured": bool(CONFIG.google_maps_api_key),
    }


@router.post("/api/prompt-filters")
@router.post("/api/discovery/prompt-filters")
def generate_filters(req: PromptRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    count = req.target_leads or req.target_lead_count
    spec = FILTER_AGENT.generate_filters(req.prompt, count)
    return {
        "prompt_summary": spec.prompt_summary,
        "target_lead_count": spec.target_lead_count,
        "catchment_locations": spec.catchment_locations,
        "positive_signals": spec.positive_signals,
        "negative_exclusions": spec.negative_exclusions,
        "location_rules": spec.location_rules,
    }


@router.post("/api/zero-api-scale-plan")
@router.post("/api/discovery/zero-api-scale-plan")
def generate_zero_api_scale_plan(req: PromptRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    target = req.target_leads or req.target_lead_count
    plan = HybridScaleOrchestrator.build_scale_plan(req.prompt, target_leads=target)
    plan_dict = asdict(plan)
    # Ensure query_clusters is provided for API consumers
    dorks = plan_dict.get("sample_dorks", [])
    clusters = [d.get("query", "") for d in dorks if isinstance(d, dict) and d.get("query")]
    plan_dict["query_clusters"] = clusters or [req.prompt]
    plan_dict["vector_allocation"] = plan_dict.get("active_vectors", [])
    plan_dict["projected_domains_to_scan"] = len(plan_dict.get("sample_dorks", [])) + len(plan_dict.get("crt_sh_endpoints", []))
    plan_dict["estimated_crawler_runtime_seconds"] = int(plan_dict.get("estimated_runtime_minutes", 1) * 60)
    return plan_dict


@router.post("/api/decode-obfuscated")
@router.post("/api/discovery/decode-obfuscated")
def decode_obfuscated_contacts(req: ObfuscatedHtmlRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    extracted = ObfuscatedContactDecoder.extract_all_from_html(req.raw_html)
    snowballed = SupplyChainSnowballSpider.extract_outbound_company_domains(
        req.raw_html, req.source_domain
    )
    return {
        "extracted": extracted,
        "snowballed_outbound_domains": snowballed,
    }


@router.get("/api/leads")
@router.get("/api/discovery/leads")
def list_leads(
    request: Request,
    client_id: Optional[str] = Query(None, description="Client Brand ID (lakhotia, shree, vrindavan, etc.)"),
    job_id: Optional[str] = Query(None, description="Campaign discovery job ID to separate newly generated leads"),
    source: Optional[str] = Query(None, description="Filter by source: live_evidence_crawler, maps_scraper_v4, etc."),
    status: Optional[str] = Query(None, description="Filter by PREPASS, REVIEW, or EXCLUDE"),
    district: Optional[str] = Query(None, description="Filter by catchment district"),
    search: Optional[str] = Query(None, description="Keyword search across company, domain, sector, or address"),
    limit: int = Query(500, ge=1, le=5000),
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    tenant_default = user.tenant_id.removeprefix("workspace--").lower().strip()
    if tenant_default in ("local-demo", "system"):
        tenant_default = "lakhotia"
    effective_client = client_id or request.headers.get("X-Matrix-Client") or tenant_default
    verify_tenant_access(user, effective_client)
    if effective_client.lower() == "all":
        client_query = "ALL"
    else:
        client_query = effective_client

    vault_leads = []
    try:
        from engine_v5.unified_pipeline import ProductionLeadVault
        vault = ProductionLeadVault(RUNTIME_ROOT / "production_vault.db")
        vault_leads = vault.list_leads(client_id=client_query, limit=limit)
    except Exception as exc:
        vault_leads = []

    seen_entities = set()
    combined_rows = []
    for r in vault_leads:
        dom = str(r.get("canonical_domain") or "").lower().strip()
        contact = str(r.get("named_contact") or r.get("director_name") or "").strip().lower()
        lead_id = str(r.get("lead_id") or "")
        entity_key = lead_id or f"{r.get('client_id')}:{dom}:{contact}"
        if entity_key not in seen_entities:
            seen_entities.add(entity_key)
            combined_rows.append(r)

    # Supabase Cloud Persistence: pull leads from cloud database scoped strictly to authorized tenant
    if SUPABASE_SYNC.is_configured:
        try:
            cloud_leads = SUPABASE_SYNC.fetch_leads(workspace_id=effective_client, limit=limit)
            for r in cloud_leads:
                r_client = str(r.get("client_id") or "")
                if client_query != "ALL" and r_client != client_query:
                    continue
                dom = str(r.get("canonical_domain") or "").lower().strip()
                contact = str(r.get("named_contact") or r.get("director_name") or "").strip().lower()
                lead_id = str(r.get("lead_id") or "")
                entity_key = lead_id or f"{r_client}:{dom}:{contact}"
                if entity_key not in seen_entities:
                    seen_entities.add(entity_key)
                    combined_rows.append(r)
        except Exception:
            pass

    # Apply filters
    rows = combined_rows
    if source and source.upper() != "ALL":
        rows = [r for r in rows if str(r.get("source") or "").lower() == source.lower()]
    if status and status.upper() != "ALL":
        rows = [r for r in rows if (r.get("qualification_status") or r.get("v4_v5_class") or r.get("status") or "").upper() == status.upper()]
    if district and district.upper() != "ALL":
        rows = [r for r in rows if district.lower() in str(r.get("catchment_district") or r.get("district") or "").lower()]
    if search:
        q = search.lower()
        rows = [
            r for r in rows
            if q in str(r.get("company_name") or r.get("company") or "").lower()
            or q in str(r.get("canonical_domain") or r.get("domain") or "").lower()
            or q in str(r.get("sector") or "").lower()
            or q in str(r.get("plant_or_warehouse_address") or r.get("address") or "").lower()
            or q in str(r.get("facility_evidence") or "").lower()
            or q in str(r.get("named_contact") or r.get("director_name") or "").lower()
            or q in str(r.get("company_phone") or r.get("phone") or "").lower()
        ]

    # Separate existing database leads from newly generated leads of the specified job_id
    if job_id:
        newly_generated_rows = [r for r in rows if str(r.get("job_id") or "") == str(job_id)]
        existing_rows = [r for r in rows if str(r.get("job_id") or "") != str(job_id)]
    else:
        newly_generated_rows = []
        existing_rows = rows

    normalized_existing = [_normalize_lead(r) for r in existing_rows[:limit]]
    normalized_newly = [_normalize_lead(r) for r in newly_generated_rows[:limit]]
    normalized_all = [_normalize_lead(r) for r in rows[:limit]]

    # Sources breakdown
    sources_breakdown = {}
    for r in rows:
        s = str(r.get("source") or "UNKNOWN")
        sources_breakdown[s] = sources_breakdown.get(s, 0) + 1

    return {
        "count": len(normalized_all),
        "client_id": effective_client,
        "job_id": job_id,
        "existing_leads": normalized_existing,
        "newly_generated_leads": normalized_newly,
        "leads": normalized_all,
        "results": normalized_all,
        "total_in_dataset": len(combined_rows),
        "live_vault_records": len(vault_leads),
        "prepass_count": sum(1 for r in combined_rows if (r.get("qualification_status") or r.get("v4_v5_class") or "").upper() == "PREPASS"),
        "review_count": sum(1 for r in combined_rows if (r.get("qualification_status") or r.get("v4_v5_class") or "").upper() == "REVIEW"),
        "exclude_count": sum(1 for r in combined_rows if (r.get("qualification_status") or r.get("v4_v5_class") or "").upper() == "EXCLUDE"),
        "sources_breakdown": sources_breakdown,
    }


@router.post("/api/discovery/ingest-maps")
def ingest_romit_maps_leads(
    payload: Dict[str, Any],
    request: Request,
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    """Ingests and normalizes leads from Romit's Google Maps scraper sidecar."""
    records = payload.get("records") or payload.get("leads") or []
    tenant_default = user.tenant_id.removeprefix("workspace--").lower().strip()
    if tenant_default in ("local-demo", "system"):
        tenant_default = "lakhotia"
    client_id = payload.get("client_id") or request.headers.get("X-Matrix-Client") or tenant_default
    verify_tenant_access(user, client_id)
    if not isinstance(records, list):
        raise HTTPException(status_code=400, detail="Payload must contain a 'records' or 'leads' list")
    
    saved, dups = RomitMapsAdapter.ingest_records(records, client_id=client_id)
    return {
        "status": "success",
        "client_id": client_id,
        "total_submitted": len(records),
        "saved_and_persisted": saved,
        "duplicates_deduplicated": dups,
        "source": "maps_scraper_v4"
    }


@router.get("/api/discovery/sources-summary")
def get_sources_summary(
    request: Request,
    client_id: Optional[str] = Query(None),
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    """Returns breakdown of database leads by origin: live_evidence_crawler vs maps_scraper_v4."""
    tenant_default = user.tenant_id.removeprefix("workspace--").lower().strip()
    if tenant_default in ("local-demo", "system"):
        tenant_default = "ALL"
    effective_client = client_id or request.headers.get("X-Matrix-Client") or tenant_default
    verify_tenant_access(user, effective_client)
    from engine_v5.unified_pipeline import ProductionLeadVault
    vault = ProductionLeadVault(RUNTIME_ROOT / "production_vault.db")
    leads = vault.list_leads(client_id=effective_client, limit=5000)
    
    breakdown = {}
    for l in leads:
        src = str(l.get("source") or "live_evidence_crawler")
        breakdown[src] = breakdown.get(src, 0) + 1
        
    return {
        "client_id": effective_client,
        "total_leads": len(leads),
        "by_source": breakdown
    }


@router.post("/api/crawl")
@router.post("/api/discovery/crawl")
async def trigger_live_crawl(req: CrawlRequest, user: User = Depends(current_user)) -> Dict[str, Any]:
    domain, reject_reason = DomainDiscoveryAgent.canonicalize_domain(req.url)
    if reject_reason:
        return {
            "domain": domain,
            "status": "SKIPPED_PRE_CRAWL",
            "reason": reject_reason,
        }
    crawler = PlaywrightVisualCrawler(CONFIG)
    crawl_data = await crawler.crawl_domain(req.url, domain)
    c = {
        "company_name": crawl_data.get("domain", domain),
        "emails": crawl_data.get("company_emails", []),
        "phones": crawl_data.get("company_phones", []),
        "directors": crawl_data.get("directors", []),
        "district": crawl_data.get("district", "West Bengal"),
    }
    crawl_data["company"] = c
    crawl_data["decoded_contacts_count"] = len(crawl_data.get("company_emails", [])) + len(crawl_data.get("company_phones", []))
    return crawl_data


@router.get("/api/export")
@router.get("/api/discovery/export")
def export_leads_csv(
    request: Request,
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(current_user),
) -> StreamingResponse:
    tenant_default = user.tenant_id.removeprefix("workspace--").lower().strip()
    if tenant_default in ("local-demo", "system"):
        tenant_default = "lakhotia"
    effective_client = client_id or request.headers.get("X-Matrix-Client") or tenant_default
    verify_tenant_access(user, effective_client)
    from engine_v5.unified_pipeline import ProductionLeadVault
    vault = ProductionLeadVault(RUNTIME_ROOT / "production_vault.db")
    leads = vault.list_leads(client_id=effective_client, limit=5000)
    if status and status.upper() != "ALL":
        leads = [r for r in leads if (r.get("qualification_status") or r.get("v4_v5_class") or "").upper() == status.upper()]
    buf = io.StringIO()
    if leads:
        fieldnames = list(leads[0].keys())
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={effective_client}_verified_leads_export.csv"},
    )


@router.post("/api/discovery/send-to-engine")
def send_discovered_leads_to_engine(
    body: SendToEngineRequest,
    user: User = Depends(current_user),
) -> Dict[str, Any]:
    """Bridge: converts discovered web leads into a standard Matrix Engine dataset."""
    effective_status = (body.status_filter or body.filter_status or "ALL").upper()
    if body.leads is not None:
        selected_leads = body.leads
    else:
        from engine_v5.unified_pipeline import ProductionLeadVault
        vault = ProductionLeadVault(RUNTIME_ROOT / "production_vault.db")
        tenant_clean = user.tenant_id.removeprefix("workspace--").lower().strip()
        selected_leads = vault.list_leads(client_id=tenant_clean if tenant_clean not in ("local-demo", "system") else "ALL", limit=5000)
        if not selected_leads:
            selected_leads = PILOT_RECORDS

    dataset_name = body.dataset_name or f"Discovered_Leads_{uuid.uuid4().hex[:8]}.csv"
    if not dataset_name.lower().endswith((".csv", ".tsv")):
        dataset_name += ".csv"

    dataset_id = str(uuid.uuid4())
    upload_dir = RUNTIME_ROOT / "uploads" / user.tenant_id / dataset_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / dataset_name

    fieldnames = [
        "company",
        "cin",
        "district",
        "state",
        "director_name",
        "phone",
        "email",
        "domain",
        "status",
        "confidence",
        "address",
        "sector",
        "facility_evidence",
    ]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for item in selected_leads:
        normalized_row = {
            "company": item.get("company_name") or item.get("company") or "",
            "cin": item.get("cin") or (item.get("wb_cins")[0] if item.get("wb_cins") else "") or "",
            "district": item.get("catchment_district") or item.get("district") or "Howrah",
            "state": item.get("state") or "West Bengal",
            "director_name": item.get("named_contact") or item.get("director_name") or "",
            "phone": item.get("company_phone") or item.get("phone") or "",
            "email": item.get("company_email") or item.get("email") or "",
            "domain": item.get("canonical_domain") or item.get("domain") or "",
            "status": item.get("qualification_status") or item.get("status") or "PREPASS",
            "confidence": str(item.get("confidence_score") or item.get("confidence") or 0.85),
            "address": item.get("plant_or_warehouse_address") or item.get("address") or "",
            "sector": item.get("sector") or "",
            "facility_evidence": item.get("facility_evidence") or "",
        }
        writer.writerow(normalized_row)

    csv_bytes = buf.getvalue().encode("utf-8")
    stored_path.write_bytes(csv_bytes)
    sha256 = hashlib.sha256(csv_bytes).hexdigest()
    size_bytes = len(csv_bytes)

    schema_json = {
        "files": [{
            "name": dataset_name,
            "stored_path": str(stored_path),
            "relative_path": dataset_name,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "inspection": {
                "detected_format": "csv",
                "headers": fieldnames,
                "filter_headers": fieldnames,
                "sheets": [{"title": "data", "rows": len(selected_leads) + 1, "columns": len(fieldnames)}],
                "sample_headers": fieldnames,
            },
        }]
    }

    with store.connect() as conn:
        conn.execute(
            "INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)",
            (dataset_id, user.tenant_id, store.now(), json.dumps(schema_json)),
        )
        conn.execute(
            "INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), dataset_id, dataset_name, str(stored_path), dataset_name, size_bytes, sha256),
        )

    store.audit(
        user.tenant_id,
        user.username,
        "lead_discovery.sent_to_engine",
        dataset_id,
        {"dataset_name": dataset_name, "lead_count": len(selected_leads), "sha256": sha256},
    )

    supabase_result = SUPABASE_SYNC.sync_leads(selected_leads)

    return {
        "status": "ok",
        "dataset_id": dataset_id,
        "dataset_name": dataset_name,
        "leads_count": len(selected_leads),
        "row_count": len(selected_leads),
        "size_bytes": size_bytes,
        "sha256": sha256,
        "supabase_sync": supabase_result,
        "supabase_sync_status": supabase_result.get("mode") or "synced",
        "message": f"Successfully converted {len(selected_leads)} discovered leads into Engine dataset '{dataset_name}'. Ready for processing.",
    }
