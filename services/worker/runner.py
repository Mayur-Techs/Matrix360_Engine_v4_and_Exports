"""Separate local worker process: claims persisted jobs and never runs inside HTTP handlers."""
from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path

from services.api import store
from services.api.settings import RUNTIME_ROOT
from .adapter import StandaloneEngineAdapter
from .exporter import create_exports


def claim_next() -> dict | None:
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not row:
            return None
        conn.execute("UPDATE jobs SET status='running', started_at=?, progress_phase='preparing', progress_percent=1, error_code=NULL, error_detail=NULL WHERE id=? AND status='queued'", (store.now(), row["id"]))
        if conn.total_changes != 1:
            return None
        return dict(row)


def set_progress(job_id: str, phase: str, percent: int, detail: str = "") -> None:
    """Persist coarse progress only; never persist source rows or PII in job metadata."""
    with store.connect() as conn:
        conn.execute(
            "UPDATE jobs SET progress_phase=?, progress_percent=?, error_detail=? WHERE id=?",
            (phase[:40], max(0, min(100, int(percent))), detail[:240] or None, job_id),
        )


def save_exports(job_id: str, tenant_id: str, artifacts: list[dict]) -> None:
    with store.connect() as conn:
        for artifact in artifacts:
            conn.execute(
                "INSERT INTO exports(id,job_id,tenant_id,name,path,content_type,size_bytes,sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), job_id, tenant_id, artifact["name"], artifact["path"], artifact["content_type"], artifact["size_bytes"], artifact["sha256"], store.now()),
            )


def process(job: dict) -> None:
    dataset_id = job["dataset_id"]
    source_dir = RUNTIME_ROOT / "uploads" / job["tenant_id"] / dataset_id
    workspace = Path(job["workspace_path"])
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        set_progress(job["id"], "validating uploads", 3)

        def source_progress(current: int, total: int, source: str) -> None:
            percent = 5 + int(75 * current / max(1, total))
            set_progress(job["id"], "classifying", percent, f"Processing source {current} of {total}: {Path(source).name}")

        report = StandaloneEngineAdapter().run(source_dir, workspace, on_progress=source_progress)
        set_progress(job["id"], "building exports", 85)
        counts, artifacts = create_exports(workspace, RUNTIME_ROOT / "exports" / job["tenant_id"] / job["id"], job["id"], job["tenant_id"], str(report.get("version", "unknown")))
        save_exports(job["id"], job["tenant_id"], artifacts)
        report["export_counts"] = counts
        status = "needs_review" if counts.get("Review_Required", 0) else "completed"
        with store.connect() as conn:
            conn.execute("UPDATE jobs SET status=?, completed_at=?, report_json=?, progress_phase='completed', progress_percent=100, error_detail=NULL WHERE id=?", (status, store.now(), json.dumps(report), job["id"]))
        store.audit(job["tenant_id"], "worker", "job.completed", job["id"], {"status": status, "counts": counts})
    except Exception as exc:  # Errors stay concise so logs do not disclose row data.
        detail = re.sub(r"[\r\n\t]+", " ", str(exc)).strip()[:240]
        with store.connect() as conn:
            conn.execute("UPDATE jobs SET status='failed', completed_at=?, error_code=?, error_detail=?, progress_phase='failed', progress_percent=100 WHERE id=?", (store.now(), type(exc).__name__, detail or None, job["id"]))
        store.audit(job["tenant_id"], "worker", "job.failed", job["id"], {"error_code": type(exc).__name__})


def run_forever(once: bool = False, interval: float = 1.0) -> None:
    store.init()
    while True:
        job = claim_next()
        if job:
            process(job)
        elif once:
            return
        else:
            time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Process at most one queued job and exit")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()
    run_forever(args.once, args.interval)

