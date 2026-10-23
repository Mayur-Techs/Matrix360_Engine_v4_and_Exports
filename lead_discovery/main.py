import sys
from pathlib import Path
_pkg_root = Path(__file__).resolve().parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
"""
FastAPI Backend for the Client-Agnostic AI Lead Discovery, Qualification & Contact Extraction Engine.
Upgraded v3.0 — Zero-API 500 to 5,000 Scale Engine (No Serper API Required!):
- Plain-English prompt -> AI-generated plain-English filters (/api/prompt-filters)
- Zero-API 8-Vector Scale Discovery Plan & Dork Matrix (/api/zero-api-scale-plan)
- Cloudflare `data-cfemail` & obfuscated HTML contact decoder (/api/decode-obfuscated)
- Supply-chain outbound domain snowball extractor (/api/snowball-extract)
- Live Playwright visual crawling (/api/crawl)
- Verified 67-domain (59 eligible) dataset query (/api/leads) & CSV export (/api/export)
"""
import csv
import io
from dataclasses import asdict
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import EngineConfig
from agents import PromptFilterAgent, DomainDiscoveryAgent
from crawler import PlaywrightVisualCrawler
from discovery_zero_api import (
    HybridScaleOrchestrator,
    ObfuscatedContactDecoder,
    SupplyChainSnowballSpider,
    KeylessSearchRotator,
)
from verified_pilot_data import PILOT_RECORDS, CSV_SHA256

app = FastAPI(
    title="AI Lead Discovery & Zero-API 5,000-Lead Extraction Engine",
    version="3.0.0",
    description=(
        "Client-agnostic, prompt-driven B2B lead discovery, qualification, and Playwright "
        "contact extraction system with 8 Zero-API OSINT discovery vectors (no Serper API required)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG = EngineConfig()
FILTER_AGENT = PromptFilterAgent()


class PromptRequest(BaseModel):
    prompt: str
    target_lead_count: int = 500


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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "zero_api_discovery_enabled": CONFIG.zero_api_discovery_enabled,
        "serper_api_required": False,
        "llm_configured": CONFIG.has_llm_key(),
        "total_verified_records": len(PILOT_RECORDS),
        "eligible_domains": sum(1 for r in PILOT_RECORDS if r["qualification_status"] in ("PREPASS", "REVIEW")),
        "csv_sha256": CSV_SHA256,
    }


@app.post("/api/config-keys")
def update_api_keys(req: ApiKeyUpdateRequest):
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
        "updated": True,
        "zero_api_discovery_enabled": CONFIG.zero_api_discovery_enabled,
        "serper_api_required": False,
        "llm_configured": CONFIG.has_llm_key(),
        "serper_configured": bool(CONFIG.serper_api_key),
        "google_maps_configured": bool(CONFIG.google_maps_api_key),
    }


@app.post("/api/prompt-filters")
def generate_filters(req: PromptRequest):
    spec = FILTER_AGENT.generate_filters(req.prompt, req.target_lead_count)
    return {
        "prompt_summary": spec.prompt_summary,
        "target_lead_count": spec.target_lead_count,
        "catchment_locations": spec.catchment_locations,
        "positive_signals": spec.positive_signals,
        "negative_exclusions": spec.negative_exclusions,
        "location_rules": spec.location_rules,
    }


@app.post("/api/zero-api-scale-plan")
def generate_zero_api_scale_plan(req: PromptRequest):
    """
    Generates a complete 500 to 5,000 lead discovery plan using all 8 Zero-API vectors
    (PIN-code x Estate Dork Matrix, OpenStreetMap Overpass QL, crt.sh SSL endpoints,
    Wayback CDX / CommonCrawl queries, and Supply-Chain Snowballing) without Serper API.
    """
    plan = HybridScaleOrchestrator.build_scale_plan(req.prompt, target_leads=req.target_lead_count)
    return asdict(plan)


@app.post("/api/decode-obfuscated")
def decode_obfuscated_contacts(req: ObfuscatedHtmlRequest):
    """
    Decodes Cloudflare `data-cfemail` XOR hex strings, JS string concatenations,
    WB GSTINs (`19...`), WB CINs, Udyam MSME numbers, and snowballed outbound domains.
    """
    extracted = ObfuscatedContactDecoder.extract_all_from_html(req.raw_html)
    snowballed = SupplyChainSnowballSpider.extract_outbound_company_domains(
        req.raw_html, req.source_domain
    )
    return {
        "extracted": extracted,
        "snowballed_outbound_domains": snowballed,
    }


@app.get("/api/leads")
def list_leads(
    status: Optional[str] = Query(None, description="Filter by PREPASS, REVIEW, or EXCLUDE"),
    district: Optional[str] = Query(None, description="Filter by catchment district"),
    search: Optional[str] = Query(None, description="Keyword search across company, domain, sector, or address"),
    limit: int = Query(500, ge=1, le=5000),
):
    rows = PILOT_RECORDS
    if status and status != "ALL":
        rows = [r for r in rows if r["qualification_status"] == status.upper()]
    if district and district != "ALL":
        rows = [r for r in rows if district.lower() in r["catchment_district"].lower()]
    if search:
        q = search.lower()
        rows = [
            r for r in rows
            if q in r["company_name"].lower()
            or q in r["canonical_domain"].lower()
            or q in r["sector"].lower()
            or q in r["plant_or_warehouse_address"].lower()
            or q in r["facility_evidence"].lower()
        ]
    return {
        "count": len(rows[:limit]),
        "total_in_dataset": len(PILOT_RECORDS),
        "prepass_count": sum(1 for r in PILOT_RECORDS if r["qualification_status"] == "PREPASS"),
        "review_count": sum(1 for r in PILOT_RECORDS if r["qualification_status"] == "REVIEW"),
        "exclude_count": sum(1 for r in PILOT_RECORDS if r["qualification_status"] == "EXCLUDE"),
        "results": rows[:limit],
    }


@app.post("/api/crawl")
async def trigger_live_crawl(req: CrawlRequest):
    domain, reject_reason = DomainDiscoveryAgent.canonicalize_domain(req.url)
    if reject_reason:
        return {
            "domain": domain,
            "status": "SKIPPED_PRE_CRAWL",
            "reason": reject_reason,
        }
    crawler = PlaywrightVisualCrawler(CONFIG)
    return await crawler.crawl_domain(req.url, domain)


@app.get("/api/export")
def export_leads_csv(status: Optional[str] = Query(None)):
    rows = PILOT_RECORDS
    if status and status != "ALL":
        rows = [r for r in rows if r["qualification_status"] == status.upper()]
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=verified_leads_export.csv"},
    )
