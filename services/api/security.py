"""Local signed-session helpers. Cloud auth is intentionally a separate deployment concern."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from time import time

from fastapi import HTTPException, Request, status

from .settings import LOCAL_PASSWORD, LOCAL_TENANT_ID, LOCAL_USERNAME, SERVICE_AUTH_MAX_AGE_SECONDS, SERVICE_AUTH_SECRET, SESSION_SECRET


@dataclass(frozen=True)
class User:
    username: str
    tenant_id: str
    role: str = "owner"


def authenticate(username: str, password: str) -> User | None:
    if hmac.compare_digest(username, LOCAL_USERNAME) and hmac.compare_digest(password, LOCAL_PASSWORD):
        return User(username=LOCAL_USERNAME, tenant_id=LOCAL_TENANT_ID)
    return None


def issue(user: User) -> str:
    payload = json.dumps({"u": user.username, "t": user.tenant_id, "r": user.role, "iat": int(time())}, separators=(",", ":")).encode()
    body = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    sig = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify(token: str | None) -> User | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(SESSION_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        decoded = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        data = json.loads(decoded)
        if data.get("u") != LOCAL_USERNAME or data.get("t") != LOCAL_TENANT_ID:
            return None
        return User(username=data["u"], tenant_id=data["t"], role=data.get("r", "owner"))
    except (ValueError, json.JSONDecodeError):
        return None


def current_user(request: Request) -> User:
    user = verify(request.cookies.get("matrix_session"))
    if user:
        return user
    service_user = verify_service_request(request)
    if service_user:
        return service_user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def verify_service_request(request: Request) -> User | None:
    """Authenticate the CRM gateway without exposing a credential to its browser.

    The CRM signs ``v1\\nMETHOD\\nPATH\\nWORKSPACE\\nTIMESTAMP\\nNONCE``. A nonce is
    accepted once, so replayed requests are rejected even within the short validity window.
    """
    if not SERVICE_AUTH_SECRET:
        return None
    workspace = request.headers.get("X-Matrix-Workspace", "")
    timestamp = request.headers.get("X-Matrix-Timestamp", "")
    nonce = request.headers.get("X-Matrix-Nonce", "")
    signature = request.headers.get("X-Matrix-Signature", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", workspace) or not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", nonce):
        return None
    try:
        issued_at = int(timestamp)
    except ValueError:
        return None
    now = int(time())
    if abs(now - issued_at) > SERVICE_AUTH_MAX_AGE_SECONDS:
        return None
    payload = "\n".join(("v1", request.method.upper(), request.url.path, workspace, str(issued_at), nonce))
    expected = hmac.new(SERVICE_AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    from .store import consume_service_nonce
    if not consume_service_nonce(nonce, issued_at + SERVICE_AUTH_MAX_AGE_SECONDS):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Service request already used")
    return User(username="crm-gateway", tenant_id=f"workspace--{workspace}", role="gateway")

