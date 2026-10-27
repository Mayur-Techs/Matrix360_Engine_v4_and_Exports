# MATRIX 360 — 2.3 MILLION ROW SCALE STATUS & RESOURCE LOGS
**Directory:** `docs/director_acceptance_20261027/17_2_3M_SCALE_STATUS_AND_RESOURCE_LOGS.md`  
**Execution Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Target:** Section 12A Corpus Processing Reality & Resource Ceiling Audit  
**Raw Benchmark Artifact:** [`docs/director_acceptance_20261027/benchmark_results_20261027.json`](file:///c:/Users/MAYUR/Downloads/Matrix360_Engine_v4_and_Exports/docs/director_acceptance_20261027/benchmark_results_20261027.json)

---

## 1. Measured Scaling Progression (100 -> 10k -> 100k -> 500k -> 2.3M Rows)

All stages were executed using synthetic data generators streaming through `engine_v5/chunked_dataset_processor.py`. Peak memory was measured via Python's standard library `tracemalloc`, and mathematical reconciliation invariants were verified on every stage:

| Stage Scale | Rows Submitted | Raw Received | Parsed Accepted | Malformed Rejected | Duplicates Collapsed | Canonical Retained | Approx Bytes | Elapsed Time | Throughput (Rows/Sec) | Peak RAM | <=40MB Partitions | Reconciliation Invariants Verified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **100 rows** | 100 | 100 | 100 | 0 | 3 | 97 | 11.6 KB | **0.003s** | 33,858 r/s | **0.02 MB** | 1 | **`True` (100% Balanced)** |
| **10k rows** | 10,000 | 10,000 | 9,901 | 99 | 300 | 9,601 | 1.15 MB | **0.158s** | 63,273 r/s | **1.02 MB** | 1 | **`True` (100% Balanced)** |
| **100k rows** | 100,000 | 100,000 | 99,001 | 999 | 3,000 | 96,001 | 11.52 MB | **2.014s** | 49,655 r/s | **10.20 MB** | 1 | **`True` (100% Balanced)** |
| **500k rows** | 500,000 | 500,000 | 495,001 | 4,999 | 15,000 | 480,001 | 57.60 MB | **11.372s** | 43,967 r/s | **42.00 MB** | 2 | **`True` (100% Balanced)** |
| **2.3M rows** | 2,300,000 | 2,300,000 | 2,277,001 | 22,999 | 69,000 | 2,208,001 | 264.96 MB | **46.263s** | **49,715 r/s** | **185.13 MB** | 7 | **`True` (100% Balanced)** |

### Mathematical Reconciliation Proof (2.3M Stage)
1. **Equation 1 (Intake Balance):**
   $$\text{raw\_received} = 2,300,000 = \text{parsed\_accepted}(2,277,001) + \text{rejected}(22,999)$$
2. **Equation 2 (Deduplication Balance):**
   $$\text{parsed\_accepted} = 2,277,001 = \text{canonical\_retained}(2,208,001) + \text{duplicates}(69,000)$$
3. **Equation 3 (Classification Balance):**
   $$\text{canonical\_retained} = 2,208,001 = \text{qualified}(2,208,001) + \text{review}(0) + \text{excluded}(0)$$

---

## 2. Text String Fidelity & Identifier Preservation Audit

To prevent silent data corruption in Microsoft Excel, Google Sheets, and downstream CRM ingestion, all identifier strings are handled as immutable text:

1. **Leading Zero Preservation:**
   * Test input: `"09876543210"`
   * Sanitizer output: `"09876543210"` (preserved exactly, warning: None).
2. **International `+91` Phone Numbers:**
   * Test input: `"+91 98310 44219"`
   * Sanitizer output: `"+91 98310 44219"` (preserved with plus intact, warning: None).
3. **20-Digit High-Precision Account / Tax Numbers:**
   * Test input: `"00001234567890123456"`
   * Sanitizer output: `"00001234567890123456"` (all 4 leading zeros preserved, warning: None).
4. **Pre-Truncated Scientific Notation Detection (`E+`):**
   * Test input: `"9.99E+17"`
   * Sanitizer output: `"9.99E+17"`, flag: `PRECISION_ALREADY_LOST_OR_UNVERIFIABLE`.
   * Never attempts to hallucinate missing digits.
5. **CSV Formula Injection Defense:**
   * Malicious spreadsheet command: `"=cmd|' /C calc'!A0"`
   * Escaped output: `"'	=cmd|' /C calc'!A0"` (prefixed with tab character to prevent DDE execution while retaining raw text).
   * Valid phone number `"+919831044219"` is recognized via regex and **not** escaped.

---

## 3. Production Architecture Assessment: Prototype vs. Worker Pipeline

1. **Current Pipeline Reality:**
   * `engine_v5/chunked_dataset_processor.py` is a **fully verified high-performance engine component and unit-test verified stream processor**.
   * It is **NOT** yet directly wired into `services/worker/runner.py`'s background Redis/SQLite job polling loop (which still delegates dataset jobs to `matrix_engine/engine/core.py`).
2. **Durability Hardening Implemented in This Run:**
   * `DurableCheckpointLedger` has been upgraded with an optional SQLite backend (`checkpoints.sqlite`).
   * Partition leases (`PENDING -> RUNNING -> COMMITTED`) are now written to disk, ensuring that container restart resilience is real and verifiable across restarts.
3. **Cloud Infrastructure Feasibility (Render Free + Supabase Free):**
   * **Supabase Free Limits:** 500 MB database, 1 GB storage, 50 MB max per file.
   * **At 264.96 MB**, the 2.3M corpus splits into **7 partitions of ~37.8 MB each**, which fits within Supabase file size limits.
   * **Render Free RAM Limit:** 512 MB. The measured peak memory during the 2.3M run was **185.13 MB**, which is safely below Render Free's 512 MB OOM ceiling.
   * **Recommendation:** For multi-gigabyte corpora exceeding 1 GB total storage, a local worker execution profile or dedicated persistent storage volume is required.
