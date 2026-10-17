"""The worker must apply the persisted job configuration, not UI-only filters."""
from __future__ import annotations

import csv
import json

from services.api import store
from services.worker import runner


def test_worker_uses_saved_export_filters_and_dataset_name(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(runner, "RUNTIME_ROOT", tmp_path)
    store.init()
    tenant_id, dataset_id, job_id = "tenant", "dataset-1", "job-1"
    source_dir = tmp_path / "uploads" / tenant_id / dataset_id
    source_dir.mkdir(parents=True)
    with (source_dir / "0000_campaign.csv").open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows([
            ["Name", "Phone", "City", "State", "Company"],
            ["Howrah industrial", "09876543210", "Howrah", "West Bengal", "Steel Works"],
            ["Kolkata industrial", "09876543211", "Kolkata", "West Bengal", "Steel Works"],
        ])
    workspace = tmp_path / "workspaces" / tenant_id / job_id
    config = {"client_profiles": ["lakhotia"], "districts": ["Howrah"], "ai_review_enabled": False}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", (dataset_id, tenant_id, store.now(), "{}"))
        conn.execute(
            "INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)",
            ("file-1", dataset_id, "campaign.csv", str(source_dir / "0000_campaign.csv"), "campaign.csv", 1, "hash"),
        )
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,config_json) VALUES(?,?,?,?,?,?,?,?)",
            (job_id, tenant_id, dataset_id, "test-idempotency-key", "running", store.now(), str(workspace), json.dumps(config)),
        )

    runner.process({"id": job_id, "tenant_id": tenant_id, "dataset_id": dataset_id, "workspace_path": str(workspace), "config_json": json.dumps(config)})

    with store.connect() as conn:
        job = conn.execute("SELECT status,report_json FROM jobs WHERE id=?", (job_id,)).fetchone()
        exports = conn.execute("SELECT name FROM exports WHERE job_id=? ORDER BY name", (job_id,)).fetchall()
    report = json.loads(job["report_json"])
    assert job["status"] == "completed"
    assert report["dataset_name"] == "campaign.csv"
    assert report["export_filters"] == {"client_profiles": ["lakhotia"], "districts": ["Howrah"]}
    assert report["export_counts"]["Lakhotia"] == 1
    assert {row["name"] for row in exports} >= {"Lakhotia.csv", "Matrix360_Combined.xlsx", "job_manifest.v1.json"}
    assert "Shree_Heights.csv" not in {row["name"] for row in exports}
