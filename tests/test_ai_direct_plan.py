"""AI Direct plans are safe metadata proposals executed by the normal worker."""
from __future__ import annotations

import json

import pytest

from services.api import app, store
from services.api.security import User


def test_ai_direct_plan_is_schema_bound_and_persisted_only_after_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant-a")
    source = tmp_path / "source.csv"
    source.write_text("Company,Industry,State,District\nNorth Steel,manufacturing,West Bengal,Howrah\n", encoding="utf-8")
    schema = {"files": [{"inspection": {"filter_headers": ["Company", "Industry", "State", "District"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-a", user.tenant_id, store.now(), json.dumps(schema)))
        conn.execute("INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)", ("file-a", "dataset-a", "source.csv", str(source), "source.csv", source.stat().st_size, "hash"))

    plan = app.create_ai_direct_plan("dataset-a", app.AudiencePlanRequest(objective="West Bengal manufacturing companies in Howrah"), user)

    assert plan["provider"]["name"] == "deterministic-schema-planner"
    assert plan["provider"]["row_data_transferred"] is False
    assert plan["approval_required"] is True
    assert {leaf["field"] for leaf in plan["predicate"]["children"]} == {"State", "Industry", "District"}
    queued = app.create_job(app.JobRequest(dataset_id="dataset-a", idempotency_key="ai-direct-test-0001", client_profiles=["lakhotia"], filter_plan=plan["predicate"], audience_plan=plan), user)
    with store.connect() as conn:
        config = json.loads(conn.execute("SELECT config_json FROM jobs WHERE id=?", (queued["job_id"],)).fetchone()["config_json"])
    assert config["filter_plan"] == plan["predicate"]
    assert config["audience_plan"]["approval_status"] == "user_confirmed"
    assert "requested_objective" not in config["audience_plan"]

    with pytest.raises(Exception, match="does not match this dataset schema"):
        app.create_job(app.JobRequest(dataset_id="dataset-a", idempotency_key="ai-direct-stale-0001", client_profiles=["lakhotia"], filter_plan=plan["predicate"], audience_plan={**plan, "schema_fingerprint": "stale"}), user)


def test_ai_direct_plan_reports_unsupported_evidence_without_a_broad_filter(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant-a")
    schema = {"files": [{"inspection": {"filter_headers": ["Vehicle Model"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-b", user.tenant_id, store.now(), json.dumps(schema)))

    plan = app.create_ai_direct_plan("dataset-b", app.AudiencePlanRequest(objective="West Bengal manufacturing companies"), user)

    assert plan["predicate"] is None
    assert plan["unknown_conditions"]
