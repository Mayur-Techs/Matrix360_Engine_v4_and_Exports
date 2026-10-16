"""Direct API handler checks; avoids socket use in the Windows desktop sandbox."""
from __future__ import annotations

import json

from services.api import app, store
from services.api.security import User


def test_job_and_audit_log_downloads_are_metadata_only(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,report_json,config_json) VALUES(?,?,?,?,?,?,?,?,?)",
            ("job-1", user.tenant_id, "dataset-1", "idempotency-key", "completed", store.now(), str(tmp_path / "workspace"), json.dumps({"active_rows": 4}), json.dumps({"client_profiles": ["lakhotia"]})),
        )
    store.audit(user.tenant_id, user.username, "job.completed", "job-1", {"status": "completed", "counts": {"Lakhotia": 1}})

    job_response = app.download_job_log("job-1", user)
    job_payload = json.loads(job_response.body)
    assert job_response.headers["content-disposition"].endswith('matrix360-job-job-1-log.json"')
    assert job_payload["job"]["report"]["active_rows"] == 4
    assert job_payload["job"]["events"][0]["action"] == "job.completed"
    assert "workspace_path" not in job_payload["job"]

    audit_response = app.download_audit_log(user)
    audit_payload = json.loads(audit_response.body)
    assert audit_response.headers["content-disposition"].endswith('matrix360-audit-log.json"')
    assert audit_payload["events"][0]["entity_id"] == "job-1"
