from __future__ import annotations

import hashlib
import hmac
from types import SimpleNamespace

import pytest

from services.api import security


def request(method: str, path: str, headers: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(method=method, url=SimpleNamespace(path=path), headers=headers, cookies={})


def signed_headers(method: str, path: str, workspace: str, nonce: str, timestamp: int) -> dict[str, str]:
    payload = "\n".join(("v1", method, path, workspace, str(timestamp), nonce))
    signature = hmac.new(b"test-gateway-secret", payload.encode(), hashlib.sha256).hexdigest()
    return {"X-Matrix-Workspace": workspace, "X-Matrix-Timestamp": str(timestamp), "X-Matrix-Nonce": nonce, "X-Matrix-Signature": signature}


def test_gateway_request_is_workspace_scoped_and_single_use(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: set[str] = set()
    def consume(nonce: str, _: int) -> bool:
        if nonce in seen:
            return False
        seen.add(nonce)
        return True
    monkeypatch.setattr(security, "SERVICE_AUTH_SECRET", "test-gateway-secret")
    monkeypatch.setattr(security, "time", lambda: 1000)
    monkeypatch.setattr("services.api.store.consume_service_nonce", consume)
    nonce = "n" * 24
    headers = signed_headers("GET", "/api/v1/datasets", "lakhotia", nonce, 1000)
    assert security.current_user(request("GET", "/api/v1/datasets", headers)).tenant_id == "workspace--lakhotia"
    with pytest.raises(Exception, match="already used"):
        security.current_user(request("GET", "/api/v1/datasets", headers))


def test_gateway_signature_cannot_be_reused_for_another_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "SERVICE_AUTH_SECRET", "test-gateway-secret")
    monkeypatch.setattr(security, "time", lambda: 1000)
    headers = signed_headers("GET", "/api/v1/datasets", "lakhotia", "m" * 24, 1000)
    assert security.verify_service_request(request("GET", "/api/v1/jobs", headers)) is None
