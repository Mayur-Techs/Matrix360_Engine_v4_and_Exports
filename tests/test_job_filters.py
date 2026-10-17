"""Job creation validates and persists export filter choices."""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException

from services.api import app, store
from services.api.security import User


def test_job_filters_are_persisted_and_require_a_client_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-1", user.tenant_id, store.now(), "{}"))

    queued = app.create_job(
        app.JobRequest(
            dataset_id="dataset-1",
            idempotency_key="filter-test-key",
            client_profiles=["lakhotia", "shree"],
            districts=["Howrah", "Howrah", " Kolkata "],
        ),
        user,
    )
    with store.connect() as conn:
        row = conn.execute("SELECT config_json FROM jobs WHERE id=?", (queued["job_id"],)).fetchone()
    assert json.loads(row["config_json"]) == {
        "ai_review_enabled": False,
        "client_profiles": ["lakhotia", "shree"],
        "districts": ["Howrah", "Kolkata"],
    }

    with pytest.raises(HTTPException, match="Choose at least one client profile"):
        app.create_job(app.JobRequest(dataset_id="dataset-1", idempotency_key="empty-profile-key", client_profiles=[]), user)
