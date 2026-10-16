"""Service contract tests without an in-process HTTP socket on Windows."""
import asyncio
import io
import json

import pytest
from fastapi import HTTPException, UploadFile

# The desktop sandbox blocks Windows asyncio's private socketpair, so an in-process
# ASGI test hangs before the first request. The equivalent local-Uvicorn smoke test
# is run separately; keep these tests visible for environments with normal sockets.
pytestmark = pytest.mark.skip(reason="Windows desktop sandbox blocks asyncio socketpair; use local Uvicorn smoke test")


def configure_runtime(monkeypatch, tmp_path):
    import services.api.settings as settings
    import services.api.store as store
    import services.api.app as api_app
    import services.worker.runner as runner

    monkeypatch.setattr(settings, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(api_app, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(runner, "RUNTIME_ROOT", tmp_path)
    store.init()
    return api_app, runner


def upload(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


def test_authenticated_upload_worker_results_and_exports(monkeypatch, tmp_path):
    from services.api.security import authenticate

    app, runner = configure_runtime(monkeypatch, tmp_path)
    user = authenticate("owner", "change-me-before-sharing")
    assert user is not None
    dataset = asyncio.run(app.upload_datasets(
        request=None,
        files=[upload("pilot.csv", b"Name,Company,City,District,Email\nA,Steel Works,Howrah,Howrah,a@example.invalid\nB,Other,Pune,,b@example.invalid\n")],
        relative_paths=json.dumps(["pilot/pilot.csv"]),
        user=user,
    ))
    queued = app.create_job(app.JobRequest(dataset_id=dataset["dataset_id"], idempotency_key="local-flow-0001"), user)
    runner.run_forever(once=True)
    job = app.get_job(queued["job_id"], user)
    assert job["status"] == "completed"
    result = app.results(queued["job_id"], user, geo_status="WB_CONFIRMED", geo_statuses=[], districts=["Howrah"], client_profiles=["lakhotia"])
    assert result["total"] == 1
    assert result["rows"][0]["lakhotia_class"] == "P2"
    exports = app.list_exports(queued["job_id"], user)["exports"]
    assert {item["name"] for item in exports} >= {"Lakhotia.csv", "Matrix360_Combined.xlsx", "job_manifest.v1.json"}


def test_rejects_unsupported_upload(monkeypatch, tmp_path):
    from services.api.security import authenticate

    app, _ = configure_runtime(monkeypatch, tmp_path)
    user = authenticate("owner", "change-me-before-sharing")
    with pytest.raises(HTTPException) as error:
        asyncio.run(app.upload_datasets(request=None, files=[upload("payload.exe", b"not-a-data-file")], relative_paths=None, user=user))
    assert error.value.status_code == 415
