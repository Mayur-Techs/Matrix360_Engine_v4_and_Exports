"""SQLite metadata store for the documented single-user local mode."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .settings import RUNTIME_ROOT


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    return RUNTIME_ROOT / "metadata.sqlite"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS datasets (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, uploaded_at TEXT NOT NULL,
              schema_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dataset_files (
              id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, original_name TEXT NOT NULL,
              stored_path TEXT NOT NULL, relative_path TEXT NOT NULL, size_bytes INTEGER NOT NULL,
              sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, dataset_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
              started_at TEXT, completed_at TEXT, workspace_path TEXT NOT NULL,
              report_json TEXT NOT NULL DEFAULT '{}', error_code TEXT, error_detail TEXT,
              progress_phase TEXT NOT NULL DEFAULT 'queued', progress_percent INTEGER NOT NULL DEFAULT 0,
              config_json TEXT NOT NULL DEFAULT '{}', UNIQUE(tenant_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS exports (
              id TEXT PRIMARY KEY, job_id TEXT NOT NULL, tenant_id TEXT NOT NULL, name TEXT NOT NULL,
              path TEXT NOT NULL, content_type TEXT NOT NULL, size_bytes INTEGER NOT NULL,
              sha256 TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL, actor TEXT NOT NULL,
              action TEXT NOT NULL, entity_id TEXT NOT NULL, created_at TEXT NOT NULL, details_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS client_profiles (
              id TEXT NOT NULL, tenant_id TEXT NOT NULL, version INTEGER NOT NULL, name TEXT NOT NULL,
              industry TEXT NOT NULL, definition_json TEXT NOT NULL, selection_plan_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL, created_by TEXT NOT NULL, retired_at TEXT,
              PRIMARY KEY(id, version)
            );
            CREATE TABLE IF NOT EXISTS filter_plans (
              id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, dataset_id TEXT NOT NULL, schema_hash TEXT NOT NULL,
              plan_json TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS service_nonces (
              nonce TEXT PRIMARY KEY, expires_at INTEGER NOT NULL
            );
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        if "config_json" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN config_json TEXT NOT NULL DEFAULT '{}'")
        if "error_detail" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN error_detail TEXT")
        if "progress_phase" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN progress_phase TEXT NOT NULL DEFAULT 'queued'")
        if "progress_percent" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")


def consume_service_nonce(nonce: str, expires_at: int) -> bool:
    """Record a gateway request nonce once; expired entries are opportunistically removed."""
    with connect() as conn:
        conn.execute("DELETE FROM service_nonces WHERE expires_at < ?", (int(datetime.now(timezone.utc).timestamp()),))
        try:
            conn.execute("INSERT INTO service_nonces(nonce,expires_at) VALUES(?,?)", (nonce, expires_at))
        except sqlite3.IntegrityError:
            return False
    return True


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def audit(tenant_id: str, actor: str, action: str, entity_id: str, details: dict[str, Any] | None = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO audit_events(tenant_id,actor,action,entity_id,created_at,details_json) VALUES(?,?,?,?,?,?)",
            (tenant_id, actor, action, entity_id, now(), json.dumps(details or {}, sort_keys=True)),
        )

