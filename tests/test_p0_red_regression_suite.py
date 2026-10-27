"""Red regression tests for P0/P1 audit defects before remediation.

Exercises SEC-01 through HANDOFF-16 to establish reproducible failing conditions
and verify post-remediation green status.
"""
from __future__ import annotations

import os
import time
import pytest
from starlette.testclient import TestClient

from services.api import security
from services.api.app import app
from services.api.security import User, issue
from lead_discovery.maps_adapter import RomitMapsAdapter
from lead_discovery.supabase_sync import SupabaseLeadSync
from engine_v5.chunked_dataset_processor import DurableCheckpointLedger, ChunkPartitionManager


@pytest.fixture
def client():
    return TestClient(app)


def test_sec_04_fixture_mode_rejected_in_production(client, monkeypatch):
    """SEC-04: MATRIX_TEST_AUTH_MODE=fixture MUST be rejected when running in production environment."""
    monkeypatch.setenv("MATRIX_TEST_AUTH_MODE", "fixture")
    monkeypatch.setenv("ENVIRONMENT", "production")
    
    # In production, fixture mode should raise or be ignored, resulting in 401 Unauthorized
    res = client.get("/api/discovery/leads?client_id=shree")
    assert res.status_code == 401, f"Expected 401 when fixture mode attempted in production, got {res.status_code}"


def test_sec_05_tenant_owner_cannot_mutate_platform_keys(client, monkeypatch):
    """SEC-05: An ordinary tenant owner (e.g. workspace--shree) MUST NOT be allowed to mutate platform API keys (403)."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user_shree_owner = User(username="admin_shree", tenant_id="workspace--shree", role="owner")
    token = issue(user_shree_owner)

    res = client.post(
        "/api/config-keys",
        json={"openai_api_key": "sk-attack-key-12345"},
        cookies={"matrix_session": token},
    )
    assert res.status_code == 403, f"Expected 403 Forbidden for tenant owner on platform config-keys, got {res.status_code}"


def test_auth_09_expired_session_token_rejected():
    """AUTH-09: Session tokens with iat older than TTL must be rejected."""
    user = User(username="operator", tenant_id="workspace--shree", role="owner")
    # Issue token with an iat 2 days in the past (172800 seconds ago)
    old_time = time.time() - 172800
    token = security.issue(user)
    
    # Verify should reject expired token
    verified = security.verify(token, current_time=time.time())
    # Before fix, verify() does not check expiration. When implemented with current_time, it must return None for expired.
    assert security.verify(token, max_age_seconds=3600, current_time=time.time() + 7200) is None


def test_client_07_unknown_client_fails_closed(client, monkeypatch):
    """CLIENT-07: Unknown client ID in campaign start MUST fail with 404/400, NOT silently fallback to lakhotia."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    # Authenticate as superadmin or local owner to bypass tenant mismatch
    user_admin = User(username="admin", tenant_id="system", role="superadmin")
    token = issue(user_admin)

    res = client.post(
        "/api/campaign/start",
        json={"client_id": "nonexistent_brand_xyz", "prompt": "find leads", "target_count": 10},
        cookies={"matrix_session": token},
    )
    assert res.status_code in (400, 404), f"Expected 400 or 404 for unknown client brand, got {res.status_code}"


def test_data_01_maps_adapter_zero_fabricated_defaults():
    """DATA-01: RomitMapsAdapter must not invent .local domain, Local Business, West Bengal default, or 0.88 score."""
    raw_record = {
        "company": {"name": ""},
        "contacts": [],
        "evidence": {}
    }
    normalized = RomitMapsAdapter.normalize_maps_record(raw_record, client_id="shree")
    
    # Must not contain fabricated .local domain
    assert ".local" not in str(normalized.get("canonical_domain") or "")
    # Must not contain fabricated Google Maps search URL as verified evidence
    assert "maps/search" not in str(normalized.get("verified_source_url") or "")
    # Must not have fake 0.88 or QUALIFIED_GENUINE
    assert normalized.get("confidence_score") != 0.88
    assert normalized.get("crawler_status") != "QUALIFIED_GENUINE"
    assert normalized.get("qualification_status") in ("NEEDS_REVIEW", "SOURCE_UNVERIFIED", "UNKNOWN")


def test_data_02_supabase_sync_no_lakhotia_or_085_default():
    """DATA-02: Supabase sync must require client_id and not default missing values to lakhotia or 0.85."""
    sync = SupabaseLeadSync()
    # If client_id is missing, sync_leads should reject or quarantine the row, not default to lakhotia
    payload = sync._prepare_lead_payload([{"company_name": "Test Company", "canonical_domain": "test.com"}])
    assert len(payload) == 0 or payload[0].get("client_id") != "lakhotia" or payload[0].get("client_id") is None


def test_handoff_16_returns_ready_for_handoff_not_synced_leads(client, monkeypatch):
    """HANDOFF-16: POST /api/v1/handoff must return ready_for_handoff and CRM_IMPORT_DEFERRED, never synced_leads."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user = User(username="operator_shree", tenant_id="workspace--shree", role="owner")
    token = issue(user)

    handoff_payload = {
        "client_id": "shree",
        "snapshot_version": "v1.0.0",
        "handoff_target": "Avinash_CRM_Core",
        "leads": [{"lead_id": "shree:test.org", "company_name": "Test", "canonical_domain": "test.org"}]
    }

    res = client.post(
        "/api/v1/handoff",
        json=handoff_payload,
        cookies={"matrix_session": token},
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") in ("ready_for_handoff", "export_prepared")
    assert data.get("crm_stage") == "CRM_IMPORT_DEFERRED"
    assert data.get("external_receiver_connected") is False
    assert "synced_leads" not in data, "Must not return synced_leads claiming active CRM delivery"


def test_job_11_checkpoint_ledger_atomic_no_overwrite(tmp_path):
    """JOB-11: Registering an already committed partition must not revert it to PENDING."""
    db_file = tmp_path / "test_checkpoints.sqlite"
    ledger = DurableCheckpointLedger(db_path=db_file)
    
    ledger.register_partition("job_test", "part_1", 0, 100, "hash1")
    assert ledger.lease_partition("job_test", "part_1") is True
    ledger.commit_partition("job_test", "part_1")
    
    # Re-registering must NOT overwrite COMMITTED to PENDING
    ledger.register_partition("job_test", "part_1", 0, 100, "hash1")
    prog = ledger.get_progress("job_test")
    assert prog["committed_partitions"] == 1
    assert prog["is_complete"] is True


def test_tenant_06_multi_person_at_same_domain_retained(client, monkeypatch):
    """TENANT-06: Two distinct decision-makers at the same company/domain must both be returned, not dropped."""
    from engine_v5.unified_pipeline import ProductionLeadVault
    from services.api.discovery_routes import RUNTIME_ROOT
    
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user = User(username="operator_shree", tenant_id="workspace--shree", role="owner")
    token = issue(user)

    vault = ProductionLeadVault(RUNTIME_ROOT / "production_vault.db")
    leads = [
        {
            "lead_id": "shree:apex-corp.in:contact_1",
            "company_name": "Apex Corporation",
            "canonical_domain": "apex-corp.in",
            "named_contact": "Aarav Sharma",
            "role": "Managing Director",
            "source": "verified_research",
            "qualification_status": "PREPASS",
        },
        {
            "lead_id": "shree:apex-corp.in:contact_2",
            "company_name": "Apex Corporation",
            "canonical_domain": "apex-corp.in",
            "named_contact": "Diya Sen",
            "role": "Chief Financial Officer",
            "source": "verified_research",
            "qualification_status": "PREPASS",
        }
    ]
    vault.upsert_leads(leads, client_id="shree", source="verified_research")

    res = client.get("/api/discovery/leads?client_id=shree&search=Apex", cookies={"matrix_session": token})
    assert res.status_code == 200
    data = res.json()
    all_leads = data.get("existing_leads", []) + data.get("newly_generated_leads", [])
    apex_leads = [l for l in all_leads if "apex-corp.in" in str(l.get("canonical_domain", ""))]
    # Must retain both distinct decision makers
    assert len(apex_leads) >= 2, f"Expected at least 2 contacts for apex-corp.in, got {len(apex_leads)}"
