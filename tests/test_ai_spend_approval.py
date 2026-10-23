"""The optional paid review needs a human approval flag and a finite cap."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api import app, store
from services.api.security import User


def _seed_dataset(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-ai", user.tenant_id, store.now(), "{}"))
    return user


def test_optional_ai_review_requires_explicit_approval_and_a_positive_cap(tmp_path, monkeypatch):
    user = _seed_dataset(tmp_path, monkeypatch)
    import services.api.settings as settings

    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_SPEND_APPROVED", False)
    monkeypatch.setattr(settings, "AI_MAX_CALLS", 5)
    with pytest.raises(HTTPException, match="MATRIX_AI_SPEND_APPROVED=true"):
        app.create_job(app.JobRequest(dataset_id="dataset-ai", idempotency_key="unapproved-review", ai_review_enabled=True), user)

    monkeypatch.setattr(settings, "AI_SPEND_APPROVED", True)
    queued = app.create_job(app.JobRequest(dataset_id="dataset-ai", idempotency_key="approved-review", ai_review_enabled=True), user)
    assert queued["status"] == "queued"
