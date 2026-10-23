"""Comprehensive tests for Matrix 360 V5 Engine Upgrade and Avinash Integration."""
from __future__ import annotations

import csv
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engine_v5.agentic_company_qualifier import (
    evaluate_vehicle_profile,
    generate_multichoice_company_filters,
    parse_inr_amount,
    qualify_and_score_lead,
)
from engine_v5.dual_drive_pipeline import DualDriveCloudBridge
from engine_v5.semantic_alias_agent import (
    ColumnMappingResult,
    SemanticAliasAgent,
    fingerprint_values,
    normalize_token_string,
)
from matrix_engine.engine.core import run as engine_run
from services.api.app import app
from services.api import security, store
from services.worker.adapter import StandaloneEngineAdapter


def test_v5_semantic_alias_layer1_exact_and_fuzzy():
    agent = SemanticAliasAgent()
    headers = [
        "Vyapar Name",
        "Full Name",
        "Mobile Number",
        "Corporate Email",
        "City",
        "State",
        "Designation",
        "Vahan No",
        "Annual Turnover",
        "Personal Aay",
    ]
    res = agent.map_dataset_headers(headers)
    m = res["canonical_index_map"]
    assert 0 in m["company"]
    assert 1 in m["name"]
    assert 2 in m["phone"]
    assert 3 in m["email"]
    assert 4 in m["city"]
    assert 5 in m["state"]
    assert 6 in m["job_title"]
    assert 7 in m["vehicle_registration"]
    assert 8 in m["annual_turnover"]
    assert 9 in m["personal_income"]


def test_v5_semantic_alias_layer2_value_fingerprinting():
    agent = SemanticAliasAgent()
    # Unclear headers with clear value patterns
    headers = ["Col_Alpha", "Col_Beta", "Col_Gamma", "Col_Delta"]
    sample_rows = [
        ["user1@example.com", "9876543210", "WB02AB1234", "₹ 50 Lakh"],
        ["user2@test.org", "+91 9876543211", "WB19CD5678", "₹ 2.5 Cr"],
        ["user3@corp.in", "9876543212", "WB06EF9012", "25 Crore"],
    ]
    res = agent.map_dataset_headers(headers, sample_rows)
    m = res["canonical_index_map"]
    assert 0 in m["email"]
    assert 1 in m["phone"]
    assert 2 in m["vehicle_registration"]
    assert 3 in m["annual_turnover"]


def test_v5_semantic_alias_layer3_learning_persistence(tmp_path):
    learned_file = tmp_path / "learned_aliases.json"
    agent = SemanticAliasAgent(learned_store_path=learned_file)
    agent.learn_alias("company", "Karkhana Naam")

    # Verify newly learned alias is recognized
    res = agent.resolve_header("Karkhana Naam")
    assert res.canonical_field == "company"
    assert res.confidence >= 0.95

    # Verify persisted to disk and reloadable by a fresh agent
    fresh_agent = SemanticAliasAgent(learned_store_path=learned_file)
    res2 = fresh_agent.resolve_header("Karkhana Naam")
    assert res2.canonical_field == "company"


def test_v5_agentic_qualifier_inr_parsing():
    assert parse_inr_amount("₹ 45 Crore") == 450_000_000
    assert parse_inr_amount("2.5 Cr") == 25_000_000
    assert parse_inr_amount("50 Lakh") == 5_000_000
    assert parse_inr_amount("₹ 75,00,000") == 7_500_000
    assert parse_inr_amount("10 k") == 10_000
    assert parse_inr_amount("") == 0
    assert parse_inr_amount(None) == 0


def test_v5_agentic_qualifier_vehicle_valuation():
    bmw = evaluate_vehicle_profile("BMW", "X5")
    assert "Luxury Executive" in bmw["tier"]
    assert bmw["estimated_inr"] >= 5_000_000

    jcb = evaluate_vehicle_profile("JCB", "3DX")
    assert "Commercial" in jcb["tier"]

    swift = evaluate_vehicle_profile("Maruti", "Swift")
    assert "Standard Utility" in swift["tier"]


def test_v5_agentic_company_qualification_and_scoring():
    profile = {
        "id": "lakhotia_v5",
        "target_state": "West Bengal",
        "priority_districts": ["Howrah", "Hooghly"],
        "sector_keywords": ["steel", "manufacturing", "foundry"],
        "min_turnover_inr": 20_000_000,
    }
    lead = {
        "company": "Howrah Heavy Foundry & Engineering Works",
        "sector": "Steel & Metal Manufacturing",
        "city": "Howrah",
        "state": "West Bengal",
        "job_title": "Managing Director & Karta",
        "annual_turnover": "₹ 50 Cr",
        "vehicle_make": "Mercedes-Benz",
        "vehicle_model": "E-Class",
    }
    result = qualify_and_score_lead(lead, profile)
    assert result["lead_class"] == "Q1"
    assert result["composite_score"] >= 80
    assert result["turnover_inr"] == 500_000_000
    assert "Geo verified" in result["reasoning_summary"]
    assert "Decision-maker" in result["reasoning_summary"]


def test_v5_multichoice_filter_generation():
    prompt = "Find industrial manufacturing plants in Howrah with turnover above 10 Cr and owner contacts"
    filters = generate_multichoice_company_filters(prompt)
    assert any(c["id"] == "manufacturing" and c["selected"] for c in filters["company_sector_choices"])
    assert any(c["id"] == "owner_cxo" and c["selected"] for c in filters["company_role_choices"])


def test_v5_dual_drive_cloud_bridge():
    bridge = DualDriveCloudBridge(
        input_folder_url_or_id="https://drive.google.com/drive/folders/input-folder-123",
        output_folder_url_or_id="https://drive.google.com/drive/folders/output-vault-456",
    )
    assert bridge.input_folder_id == "input-folder-123"
    assert bridge.output_folder_id == "output-vault-456"

    manifest = bridge.build_sync_manifest(["lakhotia", "shree"], "job-001", {"lakhotia": 42, "shree": 18})
    assert manifest["job_id"] == "job-001"
    assert len(manifest["client_exports"]) == 2
    assert manifest["client_exports"][0]["matched_leads"] == 42


def test_v5_dual_drive_rejects_identical_folders():
    with pytest.raises(ValueError, match="must be distinct"):
        DualDriveCloudBridge(
            input_folder_url_or_id="same-folder-id-1234567890",
            output_folder_url_or_id="same-folder-id-1234567890",
        )


def test_v5_engine_e2e_with_unmemorized_regional_headers(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_csv = source_dir / "unmemorized_regional.csv"

    # CSV headers in Hindi/Bengali transliterations that would fail V4 ALIASES
    with source_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Vyapar Name", "Vahan No", "Annual Turnover", "Vyakti Naam", "Mobile No", "Shahar", "Rajya"])
        writer.writerow(["Bengal Foundry Works", "WB02AB9999", "₹ 20 Cr", "Amitabh Sen", "9876543210", "Howrah", "West Bengal"])
        writer.writerow(["Hooghly Precision Tools", "WB12CD8888", "₹ 5 Cr", "Ratan Paul", "9876543211", "Hooghly", "West Bengal"])

    workspace = tmp_path / "workspace"
    report = StandaloneEngineAdapter().run(source_dir, workspace)

    assert report["version"] == "5.0.0"
    assert report["engine_mode"] == "matrix-engine-v5-agentic-dual-drive"
    assert report["active_rows"] == 2
    assert report["reconciled"] is True


def test_v5_api_endpoints_and_avinash_gateway_authentication(monkeypatch):
    seen = set()
    def consume(nonce: str, _: int) -> bool:
        if nonce in seen:
            return False
        seen.add(nonce)
        return True

    secret = "avinash-service-secret-xyz"
    monkeypatch.setattr(security, "SERVICE_AUTH_SECRET", secret)
    monkeypatch.setattr(security, "time", lambda: 1000)
    monkeypatch.setattr(store, "consume_service_nonce", consume)

    client = TestClient(app)

    # 1. Test engine info via Avinash signed request
    workspace = "avinash_crm_prod"
    timestamp = "1000"
    nonce = "v5_gateway_nonce_" + "a" * 20
    path = "/api/v1/engine/info"
    payload = f"v1\nGET\n{path}\n{workspace}\n{timestamp}\n{nonce}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    headers = {
        "X-Matrix-Workspace": workspace,
        "X-Matrix-Timestamp": timestamp,
        "X-Matrix-Nonce": nonce,
        "X-Matrix-Signature": sig,
    }
    r = client.get(path, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "5.0.0"
    assert data["tenant_id"] == f"workspace--{workspace}"
    assert "avinash_gateway_v1" in data["capabilities"]

    # 2. Test V5 schema resolve via local session
    user = security.User("owner", "local-demo")
    client.cookies.set("matrix_session", security.issue(user))
    r_schema = client.post("/api/v1/v5/schema/resolve", json={
        "headers": ["Vyapar Name", "Mobile", "Annual Turnover"]
    })
    assert r_schema.status_code == 200
    assert 0 in r_schema.json()["canonical_index_map"]["company"]
