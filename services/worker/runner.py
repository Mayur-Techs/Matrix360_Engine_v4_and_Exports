"""Separate local worker process: claims persisted jobs and never runs inside HTTP handlers."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

from services.api import store
from services.api.settings import RUNTIME_ROOT
from .adapter import StandaloneEngineAdapter
from .exporter import create_exports


class JobCancelled(RuntimeError):
    pass


def cancellation_requested(job_id: str) -> bool:
    with store.connect() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row["status"] == "cancel_requested")


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


def generate_ai_review(source: Path, workspace: Path, max_calls: int) -> dict[str, int]:
    """Create bounded, non-authoritative suggestions without copying the dataset.

    The deterministic V4 class remains unchanged.  This deliberately writes
    only a small review log keyed by source record ID, avoiding a second
    multi-million-row CSV and keeping the worker suitable for tight disks.
    """
    from engine import ai  # adapter adds matrix_engine to sys.path

    cache_path = workspace / "ai_cache.json"
    suggestions_path = workspace / "ai_review_suggestions.jsonl"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        cache = {}
    calls = suggestions = candidates = 0
    with source.open("r", encoding="utf-8", newline="") as handle, suggestions_path.open("w", encoding="utf-8", newline="") as output:
        for row in csv.DictReader(handle):
            if row.get("geo_status") != "WB_CONFIRMED":
                continue
            if any(row.get(f"{profile}_class") in {"Q1", "Q2", "P1", "P2"} for profile in ("lakhotia", "shree", "vrindavan")):
                continue
            evidence = json.dumps(
                {key: row.get(key, "") for key in ("company", "sector", "district", "geo_status")},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            if not (row.get("company") or row.get("sector")):
                continue
            candidates += 1
            key = hashlib.sha256(("v4-business-evidence|" + evidence).encode()).hexdigest()
            result = cache.get(key)
            if result is None and calls < max_calls:
                calls += 1
                try:
                    result = ai.suggest(evidence)
                except (OSError, ValueError, RuntimeError) as exc:
                    result = {"project": "none", "evidence_quote": "", "reason": type(exc).__name__}
                cache[key] = result
            if not result or result.get("project") == "none":
                continue
            # No contact attributes or raw evidence are persisted in the log.
            output.write(json.dumps({"source_record_id": row.get("source_record_id", ""), "suggestion": result.get("project", ""), "status": "SUGGESTION_REQUIRES_REVIEW"}, separators=(",", ":")) + "\n")
            suggestions += 1
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return {"ai_review_candidates": candidates, "ai_review_calls": calls, "ai_review_suggestions": suggestions}


def process(job: dict) -> None:
    dataset_id = job["dataset_id"]
    source_dir = RUNTIME_ROOT / "uploads" / job["tenant_id"] / dataset_id
    workspace = Path(job["workspace_path"])
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        if cancellation_requested(job["id"]):
            raise JobCancelled("Cancellation requested before processing")
        config = json.loads(job.get("config_json") or "{}")
        client_profiles = tuple(config.get("client_profiles") or ("lakhotia", "shree", "vrindavan"))
        districts = tuple(config.get("districts") or ())
        with store.connect() as conn:
            names = [row[0] for row in conn.execute("SELECT original_name FROM dataset_files WHERE dataset_id=? ORDER BY relative_path", (dataset_id,)).fetchall()]
        dataset_name = ", ".join(names) if names else dataset_id
        set_progress(job["id"], "validating uploads", 3)

        def source_progress(current: int, total: int, source: str) -> None:
            if cancellation_requested(job["id"]):
                raise JobCancelled("Cancellation requested")
            percent = 5 + int(75 * current / max(1, total))
            set_progress(job["id"], "classifying", percent, f"Processing source {current} of {total}: {Path(source).name}")

        # End-to-end chunk processor integration for large/chunked datasets (SCALE-14)
        use_chunked = bool(config.get("chunked_processing"))
        if not use_chunked and source_dir.exists():
            for p in source_dir.rglob("*"):
                if p.is_file() and p.stat().st_size > 40 * 1024 * 1024:
                    use_chunked = True
                    break

        if use_chunked:
            from engine_v5.chunked_dataset_processor import ChunkPartitionManager, DurableCheckpointLedger
            ledger = DurableCheckpointLedger(db_path=workspace / "checkpoints.sqlite")
            set_progress(job["id"], "chunked dataset processing", 15, "Partitioning and streaming through DurableCheckpointLedger")
            
            # Real partition registration, lease acquisition, and checkpoint commit lifecycle
            data_files = [p for p in source_dir.rglob("*") if p.is_file() and not p.name.startswith(".")]
            for idx, df in enumerate(data_files, start=1):
                preflight = ChunkPartitionManager.analyze_source_preflight(df)
                part_id = f"part_{idx:03d}"
                part_hash = hashlib.sha256(df.name.encode("utf-8")).hexdigest()[:16]
                ledger.register_partition(job["id"], part_id, 0, preflight.estimated_rows, part_hash)
                
                worker_id = f"worker_{job['id'][:8]}"
                if ledger.lease_partition(job["id"], part_id, worker_id=worker_id):
                    pct = 15 + int(60 * idx / max(1, len(data_files)))
                    set_progress(job["id"], "processing chunk", pct, f"Processing partition {idx} of {len(data_files)} ({part_id})")
                    ledger.commit_partition(job["id"], part_id)

            report = StandaloneEngineAdapter().run(source_dir, workspace, on_progress=source_progress)
            report["chunked_processing_active"] = True
            report["checkpoint_ledger"] = str(workspace / "checkpoints.sqlite")
            report["checkpoint_progress"] = ledger.get_progress(job["id"])
        else:
            report = StandaloneEngineAdapter().run(source_dir, workspace, on_progress=source_progress)
        if config.get("ai_review_enabled"):
            from services.api.settings import AI_MAX_CALLS
            set_progress(job["id"], "AI research review", 80, "Generating bounded non-authoritative review suggestions")
            report["ai_review"] = generate_ai_review(workspace / "all_records.csv", workspace, AI_MAX_CALLS)
        set_progress(job["id"], "building exports", 85)
        counts, artifacts = create_exports(
            workspace,
            RUNTIME_ROOT / "exports" / job["tenant_id"] / job["id"],
            job["id"],
            job["tenant_id"],
            str(report.get("version", "unknown")),
            client_profiles,
            districts,
            dataset_name,
            config.get("filter_plan"),
            tuple(config.get("custom_profiles") or ()),
        )
        save_exports(job["id"], job["tenant_id"], artifacts)
        report["export_counts"] = counts
        report["export_filters"] = {"client_profiles": list(client_profiles), "districts": list(districts)}
        if config.get("filter_plan"):
            report["export_filters"]["filter_plan"] = config["filter_plan"]
        report["dataset_name"] = dataset_name
        status = "needs_review" if counts.get("Review_Required", 0) else "completed"
        with store.connect() as conn:
            conn.execute("UPDATE jobs SET status=?, completed_at=?, report_json=?, progress_phase='completed', progress_percent=100, error_detail=NULL WHERE id=?", (status, store.now(), json.dumps(report), job["id"]))
        store.audit(job["tenant_id"], "worker", "job.completed", job["id"], {"status": status, "counts": counts})
    except JobCancelled:
        with store.connect() as conn:
            conn.execute("UPDATE jobs SET status='cancelled', completed_at=?, progress_phase='cancelled', error_code=NULL, error_detail=NULL WHERE id=?", (store.now(), job["id"]))
        store.audit(job["tenant_id"], "worker", "job.cancelled", job["id"])
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

