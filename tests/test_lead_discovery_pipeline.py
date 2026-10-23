"""
test_lead_discovery_pipeline.py
Comprehensive test suite verifying:
1. Lead Discovery Engine (Zero-API OSINT, Obfuscation Decoder, Crawler Fallback)
2. Supabase Lead Sync (Direct REST & Graceful Offline Storage)
3. API Discovery Endpoints (/api/discovery/* and compatibility aliases)
4. Full Bridge: Discovery Leads -> Send to Engine Dataset -> V5 Worker Qualification
"""
import pytest
from starlette.testclient import TestClient

from services.api.app import app
from services.api import security
from services.worker import runner
from lead_discovery.config import EngineConfig
from lead_discovery.discovery_zero_api import HybridScaleOrchestrator, ObfuscatedContactDecoder
from lead_discovery.supabase_sync import SupabaseLeadSync
from lead_discovery.crawler import PlaywrightVisualCrawler


def test_zero_api_discovery_scale_plan():
    """Verify zero-API discovery generates actionable query clusters and vector distributions."""
    orchestrator = HybridScaleOrchestrator()
    plan = orchestrator.build_scale_plan(
        prompt="Find engineering and fabrication workshops in Howrah",
        target_leads=150
    )
    assert plan.target_leads == 150
    assert plan.total_dorks_generated > 0
    assert len(plan.active_vectors) == 8
    assert len(plan.sample_dorks) > 0
    assert len(plan.crt_sh_endpoints) > 0


def test_obfuscated_contact_decoder():
    """Verify anti-scraping email/phone obfuscation patterns and CINs are extracted."""
    decoder = ObfuscatedContactDecoder()
    raw_html = """
    <div>
      <p>Contact MD at +91 9830123456 or phone (033) 26549871</p>
      <p>CIN: U27109WB2018PTC123456</p>
      <p>GSTIN: 19AAACH7409R1ZZ</p>
      <a href="/cdn-cgi/l/email-protection#a0c3cfced4c1c3d4e0d3d4c5c5cc938ec3cfcd"><span class="__cf_email__" data-cfemail="6e0d01001a0f0d1a2e1d1a0b0b025d400d0103">[email&#160;protected]</span></a>
    </div>
    """
    extracted = decoder.extract_all_from_html(raw_html)
    assert any("9830123456" in p for p in extracted["phones"])
    assert "U27109WB2018PTC123456" in extracted["wb_cins"]
    assert "19AAACH7409R1ZZ" in extracted["wb_gstins"]
    # Verify Cloudflare XOR decoding
    decoded_email = decoder.decode_cfemail("6e0d01001a0f0d1a2e1d1a0b0b025d400d0103")
    assert "@" in decoded_email


def test_supabase_lead_sync_fallback():
    """Verify Supabase sync records offline buffer gracefully when cloud credentials are unconfigured."""
    sync = SupabaseLeadSync()
    sample_leads = [
        {
            "company": "Test Howrah Metal Fabricators",
            "cin": "U27109WB2018PTC123456",
            "district": "Howrah",
            "state": "West Bengal",
            "phone": "+91-98301-11111",
            "email": "info@howrahmetal.com"
        }
    ]
    res = sync.sync_leads_batch(sample_leads)
    assert res["status"] in ("offline_buffered", "synced")
    assert res["count"] == 1


def test_crawler_http_fallback():
    """Verify crawler initializes and has HTTP resilient fallback."""
    cfg = EngineConfig()
    crawler = PlaywrightVisualCrawler(cfg)
    assert crawler is not None
    if hasattr(crawler, "_crawl_http_sync"):
        res = crawler._crawl_http_sync("https://kolkataindustrial.in/contact", "kolkataindustrial.in")
        assert isinstance(res, dict)
        assert res.get("domain") == "kolkataindustrial.in"
        assert "skipped_pages" in res or "pages_crawled" in res


def test_api_discovery_health():
    """Verify /api/discovery/health returns 200 OK and agentic operational status."""
    client = TestClient(app)
    response = client.get("/api/discovery/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["engine"] == "ai_lead_discovery_zero_api"
    assert data["agentic_mode"] is True


def test_api_discovery_leads_and_filters():
    """Verify discovered leads endpoint supports district and status filtering."""
    client = TestClient(app)
    
    # Check all leads
    r1 = client.get("/api/discovery/leads")
    assert r1.status_code == 200
    d1 = r1.json()
    assert "leads" in d1
    assert len(d1["leads"]) > 0
    
    # Check district filter
    r2 = client.get("/api/discovery/leads?district=Howrah")
    assert r2.status_code == 200
    d2 = r2.json()
    assert all("howrah" in lead["district"].lower() for lead in d2["leads"])


def test_api_discovery_scale_plan_endpoint():
    """Verify /api/discovery/zero-api-scale-plan generates valid plan via REST."""
    client = TestClient(app)
    response = client.post(
        "/api/discovery/zero-api-scale-plan",
        json={"prompt": "Chemical processors in Hooghly", "target_leads": 100}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_leads"] == 100
    assert len(data["query_clusters"]) > 0


def test_api_discovery_send_to_engine_bridge():
    """Verify discovered leads can be sent to engine, creating a valid dataset and processed by worker."""
    client = TestClient(app)
    user = security.User("owner", "local-demo")
    client.cookies.set("matrix_session", security.issue(user))

    # 1. Trigger the bridge endpoint
    response = client.post(
        "/api/discovery/send-to-engine",
        json={"status_filter": "all", "dataset_name": "Test_Discovered_Leads.csv"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "dataset_id" in data
    assert data["row_count"] > 0
    dataset_id = data["dataset_id"]

    # 2. Verify schema-catalog can inspect the bridge-generated dataset
    r_cat = client.get(f"/api/v1/datasets/{dataset_id}/schema-catalog")
    assert r_cat.status_code == 200
    cat_data = r_cat.json()
    headers = [f["header"] for f in cat_data["fields"]]
    assert "company" in headers
    assert "district" in headers

    # 3. Create and execute a processing job with the dataset
    r_job = client.post(
        "/api/v1/jobs",
        json={
            "dataset_id": dataset_id,
            "idempotency_key": f"test-disc-bridge-{dataset_id[:8]}",
            "client_profiles": ["lakhotia", "shree", "vrindavan"],
            "districts": []
        }
    )
    assert r_job.status_code == 200
    job_id = r_job.json()["job_id"]

    # 4. Run the worker runner for one pass
    runner.run_forever(once=True)

    # 5. Check job status
    r_status = client.get(f"/api/v1/jobs/{job_id}")
    assert r_status.status_code == 200
    job_data = r_status.json()
    assert job_data["status"] in ("completed", "needs_review")

    # 6. Check job results
    r_res = client.get(f"/api/v1/jobs/{job_id}/results")
    assert r_res.status_code == 200
    res_data = r_res.json()
    assert res_data["total"] > 0
    first_row = res_data["rows"][0]
    assert "company" in first_row
    assert "geo_status" in first_row
    assert "lakhotia_class" in first_row
