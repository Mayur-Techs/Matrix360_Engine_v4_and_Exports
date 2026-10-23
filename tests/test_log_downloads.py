"""Direct API handler checks; avoids socket use in the Windows desktop sandbox."""
from __future__ import annotations

import json

from services.api import app, store
from services.api.security import User
from fastapi import HTTPException
import pytest


def test_job_and_audit_log_downloads_are_metadata_only(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    with store.connect() as conn:
        conn.execute(
            "INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)",
            ("dataset-1", user.tenant_id, store.now(), "{}"),
        )
        conn.execute(
            "INSERT INTO dataset_files(id,dataset_id,original_name,stored_path,relative_path,size_bytes,sha256) VALUES(?,?,?,?,?,?,?)",
            ("file-1", "dataset-1", "campaign.xlsx", "unused", "campaign.xlsx", 1, "hash"),
        )
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,report_json,config_json) VALUES(?,?,?,?,?,?,?,?,?)",
            ("job-1", user.tenant_id, "dataset-1", "idempotency-key", "completed", store.now(), str(tmp_path / "workspace"), json.dumps({"active_rows": 4}), json.dumps({"client_profiles": ["lakhotia"]})),
        )
    store.audit(user.tenant_id, user.username, "job.completed", "job-1", {"status": "completed", "counts": {"Lakhotia": 1}})

    job_response = app.download_job_log("job-1", user)
    job_payload = json.loads(job_response.body)
    assert job_response.headers["content-disposition"].endswith('matrix360-job-job-1-log.json"')
    assert job_payload["job"]["report"]["active_rows"] == 4
    assert job_payload["job"]["dataset_name"] == "campaign.xlsx"
    assert job_payload["job"]["events"][0]["action"] == "job.completed"
    assert "workspace_path" not in job_payload["job"]

    jobs = app.list_jobs(user)["jobs"]
    assert jobs[0]["dataset_name"] == "campaign.xlsx"
    assert jobs[0]["export_summary"] == {"registered": 0, "available": 0}
    exports = app.list_exports("job-1", user)
    assert exports["dataset_name"] == "campaign.xlsx"
    assert exports["filters"]["client_profiles"] == ["lakhotia"]

    with store.connect() as conn:
        conn.execute(
            "INSERT INTO exports(id,job_id,tenant_id,name,path,size_bytes,sha256,content_type,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            ("missing-export", "job-1", user.tenant_id, "missing.csv", str(tmp_path / "gone.csv"), 1, "hash", "text/csv", store.now()),
        )
    exports = app.list_exports("job-1", user)["exports"]
    missing = next(item for item in exports if item["id"] == "missing-export")
    assert missing["available"] is False
    assert "path" not in missing
    jobs = app.list_jobs(user)["jobs"]
    assert jobs[0]["export_summary"] == {"registered": 1, "available": 0}
    with pytest.raises(HTTPException) as error:
        app.download_export("missing-export", user)
    assert error.value.status_code == 404

    audit_response = app.download_audit_log(user)
    audit_payload = json.loads(audit_response.body)
    assert audit_response.headers["content-disposition"].endswith('matrix360-audit-log.json"')
    assert audit_payload["events"][0]["entity_id"] == "job-1"
