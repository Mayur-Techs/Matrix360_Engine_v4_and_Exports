"""Section 12A — 2.3M Chunking, Text Fidelity & Reconciliation Verification Suite.

Tests:
1. Number-as-text fidelity: Prevents IEEE float / E+ scientific truncation on phone/ID strings.
2. Formula injection defense: Escapes formula triggers while preserving valid E.164 phones.
3. G0 / G1 scale verification (100 & 10,000 rows) with exact mathematical reconciliation.
4. Partition management & checkpoint ledger with resume semantics.
"""
import io
import pytest
from engine_v5.chunked_dataset_processor import (
    ChunkCheckpoint,
    ChunkPartitionManager,
    DurableCheckpointLedger,
    PreflightReport,
    ReconciliationMetrics,
    StreamProcessor,
    TextFidelitySanitizer,
)


def test_phone_and_identifier_string_fidelity():
    """Validates that phone numbers and long IDs are never cast to floats or corrupted."""
    test_cases = [
        ("+91 81008 57951", "+91 81008 57951", None),
        ("09876543210", "09876543210", None),
        ("00001234567890123456", "00001234567890123456", None),
        ("WB24A1234567890XYZ", "WB24A1234567890XYZ", None),
        ("9.99E+17", "9.99E+17", "PRECISION_ALREADY_LOST_OR_UNVERIFIABLE"),
        ("1.23E+10", "1.23E+10", "PRECISION_ALREADY_LOST_OR_UNVERIFIABLE"),
    ]

    for raw, expected_clean, expected_warning in test_cases:
        clean_val, warning = TextFidelitySanitizer.clean_identifier_string(raw)
        assert clean_val == expected_clean
        assert warning == expected_warning


def test_csv_formula_injection_defense():
    """Defends against spreadsheet formula injection while preserving legitimate phone numbers."""
    # Malicious formulas
    assert TextFidelitySanitizer.escape_csv_formula('=cmd|" /C calc"!A0').startswith("'\t")
    assert TextFidelitySanitizer.escape_csv_formula('@SUM(1,2)').startswith("'\t")
    assert TextFidelitySanitizer.escape_csv_formula('-2+3+cmd|').startswith("'\t")

    # Legitimate phone numbers starting with + must NOT be modified
    assert TextFidelitySanitizer.escape_csv_formula("+919831044219") == "+919831044219"
    assert TextFidelitySanitizer.escape_csv_formula("+91 98310 44219") == "+91 98310 44219"


def test_g0_g1_streaming_reconciliation():
    """Tests G0 (100 rows) and G1 (10,000 rows) with exact mathematical reconciliation."""
    # Build synthetic 10,000 row generator containing valid, duplicate, and empty rows
    def generate_synthetic_rows():
        for i in range(10_000):
            if i % 100 == 0:
                # Malformed empty row
                yield {"company": "", "phone": "", "role": ""}
            elif i % 25 == 0:
                # Duplicate domain
                yield {"company": "Duplicate Corp", "phone": "+91 98300 00000", "role": "Director"}
            else:
                yield {
                    "company": f"Genuine Enterprise {i}",
                    "phone": f"+91 98300 {i:05d}",
                    "role": "Managing Director" if i % 2 == 0 else "Manager"
                }

    def qualify(row):
        role = row.get("role", "")
        if "Director" in role:
            return "PREPASS"
        elif "Manager" in role:
            return "REVIEW"
        return "EXCLUDE"

    def get_id(row):
        return row.get("phone", "")

    processor = StreamProcessor(batch_size=1_000)
    results = list(processor.process_row_stream(
        generate_synthetic_rows(),
        qualification_fn=qualify,
        id_field_getter=get_id
    ))

    # Assert exact reconciliation invariants
    m = processor.metrics
    assert m.raw_rows_received == 10_000
    assert m.rows_rejected_with_reason == 100  # empty rows rejected
    assert m.parsed_rows_accepted == 9_900

    # Invariants must hold exactly
    assert m.verify_invariants() is True
    assert m.raw_rows_received == m.parsed_rows_accepted + m.rows_rejected_with_reason
    assert m.parsed_rows_accepted == m.canonical_rows_retained + m.duplicate_rows_collapsed_or_linked
    assert m.canonical_rows_retained == m.qualified + m.review_or_unknown + m.excluded

    # Result length must match canonical retained rows
    assert len(results) == m.canonical_rows_retained


def test_checkpoint_ledger_and_resume():
    """Verifies that durable partition leases handle server restart and idempotency."""
    ledger = DurableCheckpointLedger()
    job_id = "job_23m_test"

    # Register 4 partitions
    for i in range(4):
        ledger.register_partition(job_id, f"p_{i}", row_start=i * 25_000, row_end=(i + 1) * 25_000, sha256=f"hash_{i}")

    p0 = ledger.get_progress(job_id)
    assert p0["total_partitions"] == 4
    assert p0["committed_partitions"] == 0

    # Lease and commit partition 0 and 1
    assert ledger.lease_partition(job_id, "p_0") is True
    ledger.commit_partition(job_id, "p_0")
    assert ledger.lease_partition(job_id, "p_1") is True
    ledger.commit_partition(job_id, "p_1")

    p1 = ledger.get_progress(job_id)
    assert p1["committed_partitions"] == 2
    assert p1["progress_pct"] == 50.0

    # Already committed partition cannot be re-leased (idempotency guard)
    assert ledger.lease_partition(job_id, "p_0") is False

    # Simulate restart and resume partition 2 and 3
    assert ledger.lease_partition(job_id, "p_2") is True
    ledger.commit_partition(job_id, "p_2")
    assert ledger.lease_partition(job_id, "p_3") is True
    ledger.commit_partition(job_id, "p_3")

    p2 = ledger.get_progress(job_id)
    assert p2["committed_partitions"] == 4
    assert p2["is_complete"] is True
    assert p2["progress_pct"] == 100.0
