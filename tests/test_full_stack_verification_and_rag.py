"""Full-Stack Verification Test Suite:
1. Session Bootstrap & Bearer Token Authentication
2. AI-Approved Filter Diff Backend Persistence & Active Query
3. Real Dataset V5 Ingestion & Job Execution Endpoint
4. RAG Engine Contextual Grounding & Instant FAQ Answers
5. Zero-Fabrication Export & Ingestion Validation
"""
from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from services.api.app import app
from services.api import security, store
from services.api.security import User, issue
from services.api.rag_engine import RAGEngine
from engine_v5.unified_pipeline import ProductionLeadVault


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(RAGEngine, "VAULT_DB", tmp_path / "production_vault.db")
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    store.init()
    return TestClient(app)


def test_auth_bootstrap_and_session_status(api_client):
    """POST /api/v1/auth/bootstrap issues valid session and cookie for local/console clients."""
    # 1. Probe session anonymously -> authenticated: false
    res_session = api_client.get("/api/v1/auth/session")
    assert res_session.status_code == 200
    assert res_session.json()["authenticated"] is False

    # 2. Bootstrap session with X-Matrix-Client header
    res_boot = api_client.post(
        "/api/v1/auth/bootstrap",
        headers={"X-Matrix-Client": "lakhotia"}
    )
    assert res_boot.status_code == 200
    data = res_boot.json()
    assert data["authenticated"] is True
    assert "workspace--lakhotia" in data["tenant_id"]
    assert "token" in data
    token = data["token"]

    # 3. Access protected route with Bearer token
    res_me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_me.status_code == 200
    assert res_me.json()["username"] == security.LOCAL_USERNAME


def test_client_filter_approval_persistence(api_client):
    """POST /api/campaign/filters/approve saves approved filter diffs to SQLite."""
    user = User(username="admin", tenant_id="workspace--shree", role="owner")
    token = issue(user)

    diff_payload = {
        "client_id": "shree",
        "approved_diff": {
            "entity_mode": "person",
            "target_occupations": ["Healthcare & Medical Practitioners", "Chartered Accountants"],
            "geographic_affinities": ["Chandannagar / Hooghly"],
            "prompt": "Verified doctors and clinic heads in Chandannagar"
        }
    }

    # 1. Approve filter diff
    res_app = api_client.post(
        "/api/campaign/filters/approve",
        json=diff_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    # 2. Query active filters
    res_act = api_client.get(
        "/api/campaign/filters/active?client_id=shree",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_act.status_code == 200
    active = res_act.json()
    assert active["has_approved_filters"] is True
    assert "Healthcare & Medical Practitioners" in active["approved_filters"]["target_occupations"]

    # 3. Verify store persistence directly
    saved = store.get_approved_filters("shree")
    assert saved is not None
    assert saved["entity_mode"] == "person"


def test_rag_engine_grounding_and_faq(tmp_path):
    """RAGEngine produces grounded context and fast answers from ProductionLeadVault."""
    vault_path = tmp_path / "production_vault.db"
    vault = ProductionLeadVault(vault_path)
    RAGEngine.VAULT_DB = vault_path

    # Seed sample genuine records into vault
    leads = [
        {
            "lead_id": "shree:bcroyclinic.in:drsubhashis",
            "company_name": "Dr. B. C. Roy Diagnostic Centre",
            "canonical_domain": "bcroyclinic.in",
            "named_contact": "Dr. Subhashis Mukherjee",
            "role": "Chief Medical Officer",
            "company_phone": "+91 98310 44219",
            "catchment_district": "Chandannagar",
            "sector": "Healthcare & Diagnostics",
            "qualification_status": "PREPASS",
            "qualification_tier": "A",
            "composite_score": 95,
            "verified_source_url": "https://bcroyclinic.in",
            "ai_fit_reasoning": "Direct medical practitioner match in Chandannagar"
        },
        {
            "lead_id": "shree:auditfirm.in:cabenerjee",
            "company_name": "S. K. Banerjee & Associates",
            "canonical_domain": "auditfirm.in",
            "named_contact": "CA Sougata Banerjee",
            "role": "Senior Partner / FCA",
            "company_phone": "+91 98301 22891",
            "catchment_district": "Chandannagar",
            "sector": "Chartered Accountants",
            "qualification_status": "PREPASS",
            "qualification_tier": "A",
            "composite_score": 92,
            "verified_source_url": "https://auditfirm.in",
            "ai_fit_reasoning": "Chartered accountant resident in Hooghly"
        }
    ]
    vault.upsert_leads(leads, client_id="shree")

    # 1. Context retrieval
    ctx = RAGEngine.retrieve_grounding_context("doctors in chandannagar", client_id="shree", top_k=2)
    assert ctx["total_leads"] == 2
    assert ctx["prepass_count"] == 2
    assert "Dr. B. C. Roy Diagnostic Centre" in ctx["grounding_text"]
    assert "Dr. Subhashis Mukherjee" in ctx["grounding_text"]

    # 2. Instant FAQ - Pipeline stats
    faq_stats = RAGEngine.answer_instant_faq("How many leads are in our pipeline?", client_id="shree")
    assert faq_stats is not None
    assert "Total Saved Leads:** 2" in faq_stats["response_text"]
    assert len(faq_stats["interactive_options"]) > 0

    # 3. Instant FAQ - Top Tier-A
    faq_top = RAGEngine.answer_instant_faq("Show me top tier-a leads", client_id="shree")
    assert faq_top is not None
    assert "Dr. B. C. Roy Diagnostic Centre" in faq_top["response_text"]
    assert "+91 98310 44219" in faq_top["response_text"]

    # 4. Instant FAQ - Explain qualification
    faq_qual = RAGEngine.answer_instant_faq("Why does a lead qualify?", client_id="shree")
    assert faq_qual is not None
    assert "Chandannagar" in faq_qual["response_text"]

    # 5. Suggested questions
    questions = RAGEngine.get_suggested_questions("shree")
    assert len(questions) >= 4
    assert any("Chandannagar" in q["query"] for q in questions)


def test_suggested_questions_endpoint(api_client):
    """GET /api/campaign/ai/suggested-questions returns contextual quick questions."""
    user = User(username="admin", tenant_id="workspace--lakhotia", role="owner")
    token = issue(user)

    res = api_client.get(
        "/api/campaign/ai/suggested-questions?client_id=lakhotia&module=discovery",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["client_id"] == "lakhotia"
    assert len(data["questions"]) > 0
    assert any("Pipeline Stats" in q["label"] for q in data["questions"])


def test_v5_dataset_upload_and_job_execution(api_client, tmp_path):
    """Tests uploading a dataset file and executing a V5 processing job."""
    user = User(username="admin", tenant_id="workspace--lakhotia", role="owner")
    token = issue(user)
    headers = {"Authorization": f"Bearer {token}", "X-Matrix-Client": "lakhotia"}

    # 1. Upload sample CSV file
    csv_bytes = b"company,named_contact,role,phone,district,sector\nAcme Castings,John Doe,Director,+919830012345,Howrah,Manufacturing\n"
    files = {"files": ("test_data.csv", csv_bytes, "text/csv")}

    res_up = api_client.post("/api/v1/datasets", files=files, headers=headers)
    assert res_up.status_code == 200
    dataset_id = res_up.json()["dataset_id"]
    assert dataset_id

    # 2. Schema catalog
    res_cat = api_client.get(f"/api/v1/datasets/{dataset_id}/schema-catalog", headers=headers)
    assert res_cat.status_code == 200
    field_names = [f.get("header") or f.get("label") for f in res_cat.json()["fields"]]
    assert "company" in field_names

    # 3. Create job
    res_job = api_client.post(
        "/api/v1/jobs",
        json={
            "dataset_id": dataset_id,
            "client_profiles": ["lakhotia"],
            "districts": [],
            "idempotency_key": f"test-job-{dataset_id[:8]}"
        },
        headers=headers
    )
    assert res_job.status_code == 200
    job_id = res_job.json()["job_id"]
    assert res_job.json()["status"] == "queued"

    # 4. Trigger execution
    res_exec = api_client.post(f"/api/v1/jobs/{job_id}/execute", headers=headers)
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "execution_started"
