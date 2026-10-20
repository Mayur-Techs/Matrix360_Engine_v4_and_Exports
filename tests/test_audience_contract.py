"""Synthetic-only contract coverage for the unified dashboard handoff."""
from __future__ import annotations

import csv
import json

from services.api import app, store
from services.api.security import User
from services.worker.exporter import create_exports


def test_filter_plan_preview_and_custom_profile_are_dataset_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant-a")
    source = tmp_path / "source.csv"
    source.write_text("Company,Industry,State\nNorth Steel,manufacturing,West Bengal\nSouth Retail,retail,Maharashtra\n", encoding="utf-8")
    schema = {"files": [{"inspection": {"filter_headers": ["Company", "Industry", "State"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-a", user.tenant_id, store.now(), json.dumps(schema)))
        conn.execute("INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)", ("file-a", "dataset-a", "source.csv", str(source), "source.csv", source.stat().st_size, "hash"))
    plan = {"op": "all", "children": [{"field": "State", "operator": "eq", "value": "West Bengal"}, {"field": "Industry", "operator": "contains", "value": "manufacturing"}]}
    preview = app.preview_filter_plan("dataset-a", app.FilterPlanRequest(plan=plan), user)
    created = app.create_client_profile(app.ClientProfileRequest(name="Synthetic Manufacturing", industry="Manufacturing", audience_objective="Find observed manufacturing businesses", selection_plan=plan), user)
    job = app.create_job(app.JobRequest(dataset_id="dataset-a", idempotency_key="custom-profile-0001", client_profiles=[created["id"]]), user)

    assert preview["matched_rows"] == 1
    assert preview["truncated"] is False
    listed = app.list_client_profiles(user)
    custom = next(item for item in listed["profiles"] if item["id"] == created["id"])
    assert custom["definition"]["audience_objective"] == "Find observed manufacturing businesses"
    with store.connect() as conn:
        config = json.loads(conn.execute("SELECT config_json FROM jobs WHERE id=?", (job["job_id"],)).fetchone()["config_json"])
    assert config["custom_profiles"][0]["name"] == "Synthetic Manufacturing"


def test_custom_profile_export_uses_declared_source_fields_only(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    headers = ["geo_status", "district", "original_fields", "lakhotia_class", "shree_class", "vrindavan_class"]
    with (workspace / "all_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"geo_status": "WB_CONFIRMED", "district": "Howrah", "original_fields": json.dumps({"Industry": "manufacturing"}), "lakhotia_class": "N", "shree_class": "N", "vrindavan_class": "N"})
        writer.writerow({"geo_status": "WB_CONFIRMED", "district": "Howrah", "original_fields": json.dumps({"Industry": "retail"}), "lakhotia_class": "N", "shree_class": "N", "vrindavan_class": "N"})
    counts, artifacts = create_exports(
        workspace, tmp_path / "exports", "job-a", "tenant-a", "test", client_profiles=("profile-a",),
        custom_profiles=({"id": "profile-a", "name": "Synthetic Manufacturing", "selection_plan": {"field": "Industry", "operator": "contains", "value": "manufacturing"}},),
    )
    assert counts["Synthetic Manufacturing"] == 1
    assert any(item["name"] == "Synthetic Manufacturing.csv" for item in artifacts)


def test_cancelled_job_is_not_visible_as_another_tenant(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    owner, other = User(username="owner", tenant_id="tenant-a"), User(username="other", tenant_id="tenant-b")
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-a", owner.tenant_id, store.now(), "{}"))
    job = app.create_job(app.JobRequest(dataset_id="dataset-a", idempotency_key="cancel-test-0001", client_profiles=["lakhotia"]), owner)
    assert app.cancel_job(job["job_id"], owner)["status"] == "cancelled"
    try:
        app.get_job(job["job_id"], other)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404
    else:
        raise AssertionError("cross-tenant job was visible")
