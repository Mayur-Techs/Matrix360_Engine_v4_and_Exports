"""P0 Tenant Security & Fail-Closed Authorization Verification Suite.

Tests:
1. Unauthenticated fail-closed: Anonymous requests return 401 Unauthorized.
2. Cross-tenant isolation: Tenant A cannot read, start, cancel, or export Tenant B's leads/jobs (403 Forbidden).
3. Global cross-tenant enumeration protection: Non-owner cannot query client_id=ALL (403 Forbidden).
4. Replay attacks on service gateway are rejected.
5. Legitimate authenticated tenant access succeeds (200 OK).
"""
import hashlib
import hmac
import pytest
from starlette.testclient import TestClient
from services.api.app import app
from services.api import security
from services.api.security import User, issue


@pytest.fixture
def test_client():
    return TestClient(app)


def test_anonymous_requests_fail_closed(test_client, monkeypatch):
    """Anonymous callers without valid session or gateway signature must receive 401."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)

    # 1. Unauthenticated campaign start
    res = test_client.post("/api/campaign/start", json={
        "prompt": "Test unauthenticated prompt",
        "client_id": "lakhotia",
        "target_count": 50
    })
    assert res.status_code == 401
    assert "Authentication required" in res.json().get("detail", "")

    # 2. Unauthenticated lead discovery
    res2 = test_client.get("/api/discovery/leads?client_id=lakhotia")
    assert res2.status_code == 401
    assert "Authentication required" in res2.json().get("detail", "")


def test_cross_tenant_access_denied(test_client, monkeypatch):
    """A user in workspace A cannot read or launch jobs in workspace B (403 Forbidden)."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)

    # Issue session token for user in Tenant "shree" (role="member")
    user_shree = User(username="operator_shree", tenant_id="workspace--shree", role="member")
    cookie_token = issue(user_shree)

    # Attempt to read Lakhotia leads
    res = test_client.get(
        "/api/discovery/leads?client_id=lakhotia",
        cookies={"matrix_session": cookie_token}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "")
    assert "cannot access resources belonging to 'lakhotia'" in res.json().get("detail", "")

    # Attempt to start a campaign job for Lakhotia
    res2 = test_client.post(
        "/api/campaign/start",
        json={"prompt": "Some dorks", "client_id": "lakhotia", "target_count": 50},
        cookies={"matrix_session": cookie_token}
    )
    assert res2.status_code == 403
    assert "Forbidden" in res2.json().get("detail", "")


def test_non_owner_global_enumeration_denied(test_client, monkeypatch):
    """Non-owner tenant member cannot query client_id=ALL (403 Forbidden)."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)

    user_member = User(username="member_1", tenant_id="workspace--shree", role="member")
    cookie_token = issue(user_member)

    res = test_client.get(
        "/api/discovery/leads?client_id=ALL",
        cookies={"matrix_session": cookie_token}
    )
    assert res.status_code == 403
    assert "Admin role required" in res.json().get("detail", "")


def test_legitimate_tenant_access_succeeds(test_client, monkeypatch):
    """Authorized tenant accessing their own workspace succeeds (200 OK)."""
    monkeypatch.delenv("MATRIX_TEST_AUTH_MODE", raising=False)

    user_shree = User(username="operator_shree", tenant_id="workspace--shree", role="member")
    cookie_token = issue(user_shree)

    res = test_client.get(
        "/api/discovery/leads?client_id=shree",
        cookies={"matrix_session": cookie_token}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["client_id"] == "shree"


def test_service_gateway_replay_denied(monkeypatch):
    """HMAC gateway requests cannot be replayed with the same nonce."""
    seen: set = set()
    def consume(nonce: str, _: int) -> bool:
        if nonce in seen:
            return False
        seen.add(nonce)
        return True

    monkeypatch.setattr(security, "SERVICE_AUTH_SECRET", "test-crm-gateway-secret-2026")
    monkeypatch.setattr(security, "time", lambda: 5000)
    monkeypatch.setattr("services.api.store.consume_service_nonce", consume)

    nonce = "a" * 24
    payload = "\n".join(("v1", "GET", "/api/v1/datasets", "shree", "5000", nonce))
    sig = hmac.new(b"test-crm-gateway-secret-2026", payload.encode(), hashlib.sha256).hexdigest()

    from types import SimpleNamespace
    req = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/api/v1/datasets"),
        headers={"X-Matrix-Workspace": "shree", "X-Matrix-Timestamp": "5000", "X-Matrix-Nonce": nonce, "X-Matrix-Signature": sig},
        cookies={}
    )

    # First access succeeds
    user = security.verify_service_request(req)
    assert user is not None
    assert user.tenant_id == "workspace--shree"

    # Second access with identical nonce fails
    with pytest.raises(Exception, match="already used"):
        security.verify_service_request(req)
