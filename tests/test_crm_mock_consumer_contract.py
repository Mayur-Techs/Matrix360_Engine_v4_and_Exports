"""Avinash CRM Deferred Handoff Mock Consumer & Contract Verification Suite.

Validates Section 8 of the Director P0 Directive:
- audience-export.v1 JSON contract structure
- Handoff package preparation via POST /api/v1/handoff/prepare and POST /api/v1/handoff
- Cryptographic hash verification and tamper detection
- Status honesty: ready_for_handoff, CRM_IMPORT_DEFERRED, external_receiver_connected=false
- Unauthorized tenant denial
- Mock-only consumer reconciliation without live network/CRM connection
"""
from __future__ import annotations

import hashlib
import json
import pytest
from starlette.testclient import TestClient

from services.api.app import app
from services.api.security import User, issue


@pytest.fixture
def client():
    return TestClient(app)


def test_handoff_prepare_and_schema_validation(client, monkeypatch):
    """POST /api/v1/handoff/prepare produces a compliant audience-export.v1 package."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user = User(username="operator_shree", tenant_id="workspace--shree", role="owner")
    token = issue(user)

    leads_payload = [
        {
            "lead_id": "shree:bcroyclinic-chd.in:drsubhashis",
            "company_name": "Dr. B. C. Roy Diagnostic & Clinic Centre",
            "canonical_domain": "bcroyclinic-chd.in",
            "named_contact": "Dr. Subhashis Mukherjee",
            "role": "Chief Medical Officer",
            "phone": "+91 98310 44219",
            "email": "dr.subhashis@bcroyclinic-chd.in",
            "catchment_district": "Chandannagar",
            "qualification_tier": "A",
            "confidence_score": 0.92,
            "source": "maps_scraper_v4",
            "verified_source_url": "https://bcroyclinic-chd.in",
            "crm_stage": "READY_FOR_HANDOFF",
        }
    ]

    res = client.post(
        "/api/v1/handoff/prepare",
        json={
            "client_id": "shree",
            "snapshot_version": "v1.0.0",
            "handoff_target": "Avinash_CRM_Core",
            "leads": leads_payload,
        },
        cookies={"matrix_session": token},
    )
    assert res.status_code == 200
    data = res.json()

    # Contract assertions
    assert data["status"] == "ready_for_handoff"
    assert data["client_id"] == "shree"
    assert data["record_count"] == 1
    assert data["crm_stage"] == "CRM_IMPORT_DEFERRED"
    assert data["external_receiver_connected"] is False
    assert data["export_artifact_ready"] is True
    assert "idempotency_hash" in data
    assert len(data["idempotency_hash"]) == 64

    # Verify cryptographic idempotency hash
    expected_hash = hashlib.sha256(json.dumps(leads_payload, sort_keys=True).encode("utf-8")).hexdigest()
    assert data["idempotency_hash"] == expected_hash


def test_mock_consumer_tamper_detection(client, monkeypatch):
    """Mock CRM consumer rejects payload if content has been tampered with or hash does not match."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user = User(username="operator_shree", tenant_id="workspace--shree", role="owner")
    token = issue(user)

    leads = [{"lead_id": "shree:lead_01", "name": "Dr. A"}]
    res = client.post(
        "/api/v1/handoff",
        json={"client_id": "shree", "leads": leads, "snapshot_version": "v1.0.0", "handoff_target": "Avinash_CRM_Core"},
        cookies={"matrix_session": token},
    )
    assert res.status_code == 200
    package = res.json()
    claimed_hash = package["idempotency_hash"]

    # Consumer verifies package integrity
    def verify_package(p_leads: list, p_hash: str) -> bool:
        computed = hashlib.sha256(json.dumps(p_leads, sort_keys=True).encode("utf-8")).hexdigest()
        return computed == p_hash

    # Authentic package verifies
    assert verify_package(leads, claimed_hash) is True

    # Tampered package (e.g. modified contact or injected row) fails integrity check
    tampered_leads = [{"lead_id": "shree:lead_01", "name": "Dr. A"}, {"lead_id": "injected", "name": "Attacker"}]
    assert verify_package(tampered_leads, claimed_hash) is False


def test_cross_tenant_handoff_rejection(client, monkeypatch):
    """Tenant Alpha cannot prepare or export handoff package for Tenant Beta."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)
    user_alpha = User(username="user_alpha", tenant_id="workspace--tenant_alpha", role="owner")
    token = issue(user_alpha)

    res = client.post(
        "/api/v1/handoff/prepare",
        json={"client_id": "tenant_beta", "leads": [], "snapshot_version": "v1.0.0", "handoff_target": "Avinash_CRM_Core"},
        cookies={"matrix_session": token},
    )
    assert res.status_code == 403
    assert "cannot access" in res.json().get("detail", "").lower()
