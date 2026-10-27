# 04 — Chunked Worker and 2.3M Reality Validation

**Date:** 27 October 2026  
**Engineer:** Mayur (`Mayur-Techs`)  
**Components:** `engine_v5/chunked_dataset_processor.py`, `services/worker/runner.py`, `tests/test_file_backed_streaming_scale.py`

---

## 1. Chunked Worker Execution Loop

In `services/worker/runner.py`, the large-file detection branch connects directly to the `ChunkPartitionManager` and `DurableCheckpointLedger`:

1. **Preflight Analysis:** `ChunkPartitionManager.analyze_source_preflight()` inspects file size, encoding (strict UTF-8 / utf-8-sig fallback), headers, and candidate identifiers without buffering the full dataset in RAM.
2. **Partition Slicing & Storage Ceilings:** Slices inputs into `<40 MB` partitions to stay strictly within Supabase Storage 50 MB free-tier limits.
3. **Partition Registration:** Each partition is registered with `DurableCheckpointLedger.register_partition()` with row range and SHA-256 hash. `ON CONFLICT DO NOTHING` protects committed partitions from accidental regression upon worker restart.
4. **Atomic Lease Acquisition:** `DurableCheckpointLedger.lease_partition()` uses atomic SQLite `UPDATE ... WHERE status IN ('PENDING', 'FAILED') OR (status = 'RUNNING' AND updated_at < ?)` to prevent double-processing.
5. **Progress & Commit:** Reports partition progress (`partition N of M`) and records `status = 'COMMITTED'` in `checkpoints.sqlite`.

---

## 2. 2.3-Million Record Processing Reality

- **Synthetic Benchmark Validation:**
  - Ingested 2,300,000 synthetic rows through streaming qualification in `46.26 seconds` on local hardware.
  - Peak RAM stayed at `~185 MB`, well below the 512 MB Render Free tier limit.
- **Identifier Fidelity (`TextFidelitySanitizer`):**
  - Phone numbers preserved with leading zeros and `+91` prefix (e.g. `+91 98310 44219`).
  - Irrecoverable scientific notation (`1.23E+11`) detected and flagged as corrupted without fabricating missing digits.
  - CSV formula injection mitigated by escaping leading `=`, `+`, `-`, `@`.
- **Honest Cloud Feasibility Classification:**
  - Files `<= 40 MB`: `FEASIBLE` directly in free-tier cloud.
  - Files `40 MB – 1 GB`: `PARTITIONED_STORAGE_REQUIRED` (processed in `<40 MB` chunks).
  - Files `> 1 GB`: `LOCAL_ASSISTED_REQUIRED` (exceeds Supabase 1 GB free-tier quota; processed via local streaming engine).
