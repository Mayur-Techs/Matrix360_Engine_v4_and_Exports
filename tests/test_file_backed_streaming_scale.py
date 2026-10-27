"""File-backed streaming, exact text fidelity, and crash-recovery verification suite.

Validates Section 6 of the Director P0 Directive:
- Real file-backed streaming (not in-memory generator)
- Exact identifier string preservation (no E+ float conversion, leading zeros preserved)
- Formula injection defense
- Checkpoint persistence and crash restart
- Exact mathematical reconciliation invariants
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from engine_v5.chunked_dataset_processor import (
    ChunkPartitionManager,
    DurableCheckpointLedger,
    StreamProcessor,
    TextFidelitySanitizer,
)


def test_text_fidelity_preserves_leading_zeros_and_long_numbers():
    """TextFidelitySanitizer preserves exact phone numbers, CIN/GSTIN codes, and leading zeros."""
    # 1. Leading zero preservation
    clean, warn = TextFidelitySanitizer.clean_identifier_string("001234567890")
    assert clean == "001234567890"
    assert warn is None

    # 2. International E.164 phone
    clean_phone, warn_p = TextFidelitySanitizer.clean_identifier_string("+91 98310 44219")
    assert clean_phone == "+91 98310 44219"
    assert warn_p is None

    # 3. Detection of pre-corrupted float notation from prior flawed systems
    corrupted, warn_c = TextFidelitySanitizer.clean_identifier_string("9.83104e+11")
    assert corrupted == "9.83104e+11"
    assert warn_c == "PRECISION_ALREADY_LOST_OR_UNVERIFIABLE"

    # 4. Formula injection defense
    escaped_cmd = TextFidelitySanitizer.escape_csv_formula("=cmd|' /C calc'!A0")
    assert escaped_cmd.startswith("'\t=")

    # Leading + on international phone number is NOT neutralized as formula
    phone_safe = TextFidelitySanitizer.escape_csv_formula("+91 9831044219")
    assert phone_safe == "+91 9831044219"


def test_file_backed_streaming_and_reconciliation(tmp_path):
    """Streams a physical CSV file through StreamProcessor, verifying exact row accounting."""
    csv_file = tmp_path / "test_leads_corpus.csv"

    # Write a test file with genuine, duplicate, empty, and invalid rows
    records = [
        ["canonical_domain", "company_name", "named_contact", "phone", "district", "sector"],
        # Valid lead 1
        ["apex-corp.in", "Apex Corporation", "Aarav Sharma", "+91 98310 11111", "Howrah", "Manufacturing"],
        # Valid lead 2 (same company, different person - People-First)
        ["apex-corp.in", "Apex Corporation", "Diya Sen", "+91 98310 22222", "Howrah", "Finance"],
        # Duplicate lead 1 (exact duplicate of lead 1)
        ["apex-corp.in", "Apex Corporation", "Aarav Sharma", "+91 98310 11111", "Howrah", "Manufacturing"],
        # Empty row
        ["", "", "", "", "", ""],
        # Valid lead 3
        ["mukherjee-clinic.org", "Mukherjee Clinic", "Dr. Subhashis Mukherjee", "+91 98310 44219", "Chandannagar", "Healthcare"],
    ]

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(records)

    # 1. Run Preflight
    report = ChunkPartitionManager.analyze_source_preflight(csv_file)
    assert report.total_bytes > 0
    assert report.estimated_rows == 5  # 5 data rows
    assert report.detected_encoding in ("utf-8", "utf-8-sig")

    # 2. Stream & Process
    def row_gen():
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield row

    processor = StreamProcessor(batch_size=100)
    output_rows = list(processor.process_row_stream(
        row_generator=row_gen(),
        qualification_fn=lambda r: "PREPASS" if r.get("named_contact") else "REVIEW",
        id_field_getter=lambda r: f"{r.get('canonical_domain')}:{r.get('named_contact')}",
    ))

    # Invariants verification
    m = processor.metrics
    assert m.raw_rows_received == 5
    assert m.rows_rejected_with_reason == 1  # 1 empty row
    assert m.parsed_rows_accepted == 4
    assert m.duplicate_rows_collapsed_or_linked == 1  # 1 duplicate collapsed
    assert m.canonical_rows_retained == 3  # 3 distinct person-level records
    assert m.qualified == 3
    assert m.verify_invariants() is True
    assert len(output_rows) == 3


def test_crash_recovery_checkpoint_state_machine(tmp_path):
    """Simulates a mid-processing worker crash and verifies that committed partitions resume safely."""
    ledger_db = tmp_path / "durable_checkpoints.sqlite"
    ledger = DurableCheckpointLedger(db_path=ledger_db)

    # Register 3 partitions
    ledger.register_partition("job_crash_test", "part_1", 0, 50000, "hash1")
    ledger.register_partition("job_crash_test", "part_2", 50001, 100000, "hash2")
    ledger.register_partition("job_crash_test", "part_3", 100001, 150000, "hash3")

    # Worker 1 leases and commits part_1
    assert ledger.lease_partition("job_crash_test", "part_1", worker_id="worker-1") is True
    ledger.commit_partition("job_crash_test", "part_1")

    # Worker 1 leases part_2, then crashes (simulated by stale lease timeout)
    assert ledger.lease_partition("job_crash_test", "part_2", worker_id="worker-1") is True

    # Fresh worker instance starts after restart
    ledger_recovered = DurableCheckpointLedger(db_path=ledger_db)
    prog = ledger_recovered.get_progress("job_crash_test")
    assert prog["total_partitions"] == 3
    assert prog["committed_partitions"] == 1
    assert prog["running_partitions"] == 1

    # Part_1 cannot be leased again
    assert ledger_recovered.lease_partition("job_crash_test", "part_1", worker_id="worker-2") is False

    # Simulate stale lease timeout (lease_timeout_seconds=0) to recover crashed part_2
    reclaimed = ledger_recovered.lease_partition("job_crash_test", "part_2", worker_id="worker-2", lease_timeout_seconds=0.0)
    assert reclaimed is True

    # Complete part_2 and part_3
    ledger_recovered.commit_partition("job_crash_test", "part_2")
    assert ledger_recovered.lease_partition("job_crash_test", "part_3", worker_id="worker-2") is True
    ledger_recovered.commit_partition("job_crash_test", "part_3")

    final_prog = ledger_recovered.get_progress("job_crash_test")
    assert final_prog["committed_partitions"] == 3
    assert final_prog["is_complete"] is True
    assert final_prog["progress_pct"] == 100.0
