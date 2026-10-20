"""AI Direct plans are safe metadata proposals executed by the normal worker."""
from __future__ import annotations

import json

import pytest

from services.api import app, store
from services.api import audience_plan
from services.api.security import User


def test_ai_direct_plan_is_schema_bound_and_persisted_only_after_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setenv("MATRIX_AI_PIPELINE_ENABLED", "false")
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
    monkeypatch.setenv("MATRIX_AI_PIPELINE_ENABLED", "false")
    store.init()
    user = User(username="owner", tenant_id="tenant-a")
    schema = {"files": [{"inspection": {"filter_headers": ["Vehicle Model"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-b", user.tenant_id, store.now(), json.dumps(schema)))

    plan = app.create_ai_direct_plan("dataset-b", app.AudiencePlanRequest(objective="West Bengal manufacturing companies"), user)

    assert plan["predicate"] is None
    assert plan["unknown_conditions"]


def test_each_model_mode_receives_only_its_bounded_context(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MATRIX_AI_PIPELINE_ENABLED", "true")
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({
                "output_text": json.dumps({
                    "conditions": [
                        {"field": "State", "operator": "contains", "value": "west bengal"},
                        {"field": "Industry", "operator": "contains", "value": "manufacturing"},
                    ],
                    "segment_explanation": ["Uses explicit business objective terms and available schema fields."],
                    "unknown_conditions": [],
                }),
                "usage": {"input_tokens": 12, "output_tokens": 8, "total_tokens": 20},
            }).encode()

    def fake_urlopen(request, timeout):
        captured.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(audience_plan.urllib.request, "urlopen", fake_urlopen)
    store.init()
    user = User(username="owner", tenant_id="tenant-a")
    schema = {"files": [{"inspection": {"filter_headers": ["Name", "Email", "Company", "Industry", "State", "District"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-c", user.tenant_id, store.now(), json.dumps(schema)))

    assisted = app.create_ai_assisted_plan("dataset-c", app.AudiencePlanRequest(objective="West Bengal manufacturing companies"), user)
    direct = app.create_ai_direct_plan("dataset-c", app.AudiencePlanRequest(objective="West Bengal manufacturing companies", profile_id="lakhotia"), user)

    assert assisted["provider"]["name"] == "openai-responses"
    assert assisted["provider"]["context_scope"] == "objective+safe-schema"
    assert direct["provider"]["context_scope"] == "profile+objective+safe-schema"
    assert {item["field"] for item in assisted["predicate"]["children"]} == {"State", "Industry"}
    assisted_context = json.loads(captured[0]["input"])
    direct_context = json.loads(captured[1]["input"])
    assert assisted_context["profile_context"] is None
    assert direct_context["profile_context"]["name"] == "Lakhotia Industrial"
    assert {field["header"] for field in assisted_context["eligible_fields"]}.isdisjoint({"Name", "Email"})
    assert "source rows" not in captured[0]["instructions"]
