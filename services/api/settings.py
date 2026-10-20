"""Small dependency-free local configuration loader."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    # Process environment variables always win. A local override is loaded
    # after .env so credentials can remain outside the shared development file.
    inherited = set(os.environ)
    for path in (ROOT / ".env", ROOT / ".env.local"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in inherited:
                os.environ[key] = value.strip()


_load_dotenv()
RUNTIME_ROOT = Path(os.getenv("MATRIX_STORAGE_ROOT", str(ROOT / "runtime"))).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("MATRIX_MAX_UPLOAD_BYTES", "536870912"))
DEPLOYMENT_MODE = os.getenv("MATRIX_DEPLOYMENT_MODE", "local").lower()
LOCAL_USERNAME = os.getenv("MATRIX_LOCAL_USERNAME", "owner")
LOCAL_PASSWORD = os.getenv("MATRIX_LOCAL_PASSWORD", "change-me-before-sharing")
LOCAL_TENANT_ID = os.getenv("MATRIX_LOCAL_TENANT_ID", "local-demo")
SESSION_SECRET = os.getenv("MATRIX_SESSION_SECRET", "local-development-only-change-before-sharing")
SERVICE_AUTH_SECRET = os.getenv("MATRIX_SERVICE_AUTH_SECRET", "")
SERVICE_AUTH_MAX_AGE_SECONDS = int(os.getenv("MATRIX_SERVICE_AUTH_MAX_AGE_SECONDS", "300"))
COOKIE_SECURE = os.getenv("MATRIX_COOKIE_SECURE", "true" if DEPLOYMENT_MODE != "local" else "false").lower() == "true"
AI_PROVIDER = os.getenv("MATRIX_AI_PROVIDER", "openai")
AI_MODEL = os.getenv("MATRIX_AI_MODEL", "gpt-4o-mini")
AI_REVIEW_MODEL = os.getenv("MATRIX_AI_REVIEW_MODEL", "gpt-4o")
AI_ENABLED = os.getenv("MATRIX_AI_ENABLED", "false").lower() == "true"
AI_MAX_CALLS = int(os.getenv("MATRIX_AI_MAX_CALLS", "0"))
AI_ALLOW_PII = os.getenv("MATRIX_AI_ALLOW_PII", "false").lower() == "true"
AI_PIPELINE_ENABLED = os.getenv("MATRIX_AI_PIPELINE_ENABLED", "false").lower() == "true"
AI_PLANNER_MODEL = os.getenv("MATRIX_AI_PLANNER_MODEL", AI_MODEL)
AI_DIRECT_MODEL = os.getenv("MATRIX_AI_DIRECT_MODEL", AI_MODEL)


def validate_deployment_settings() -> None:
    """Reject known development credentials whenever this is not local-only mode."""
    insecure = {
        "MATRIX_LOCAL_PASSWORD": LOCAL_PASSWORD == "change-me-before-sharing",
        "MATRIX_SESSION_SECRET": SESSION_SECRET == "local-development-only-change-before-sharing",
    }
    if DEPLOYMENT_MODE != "local" and any(insecure.values()):
        missing = ", ".join(name for name, is_default in insecure.items() if is_default)
        raise RuntimeError(f"Refusing non-local startup with development defaults: {missing}")

