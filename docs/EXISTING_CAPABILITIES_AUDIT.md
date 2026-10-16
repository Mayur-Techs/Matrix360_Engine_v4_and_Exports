# Existing capabilities audit — 16 October 2026

## Evidence examined

- **VERIFIED:** this delivery contains `matrix_engine/`, six Python engine modules, two test files, five pre-generated exports and `VALIDATION.json`.
- **VERIFIED:** it is not a Git checkout (`git status` reports no repository) and has no V4 source tree, v2.1/v2.2 archive, console POC, Docker setup, FastAPI service or browser UI.
- **VERIFIED:** `matrix_engine/README.md` identifies itself as a new standalone 3.0 implementation; `engine/targeting.py` reports rule version `4.0.0`. A version string is not proof of canonical V4 provenance.
- **REPORTED:** `VALIDATION.json` claims 13 tests and a 10,054-row reconciliation. It is retained as historical evidence only.

## Reusable capability matrix

| Capability | Evidence | Decision |
| --- | --- | --- |
| Chunked CSV/XLSX/XLS/XLSB ingestion | `engine/core.py` writes 10,000-row Parquet batches | Reuse behind adapter |
| DuckDB warehouse and source-version ledger | `engine/core.py` | Reuse for local worker |
| Conservative geography and three independent classifications | `engine/targeting.py` | Reuse as research-only rules |
| Formula-safe legacy workbook export | `export.mjs` | Replace with Python server exporter; old exporter loads all rows |
| Optional AI review | `engine/ai.py` | Retain disabled by default; do not auto-promote a lead |
| Browser upload/jobs/results/auth/RBAC | Absent | Implement local pilot console |
| Canonical V4 classifier | Absent | Blocked; visibly label adapter mode |

## Known gaps and repairs

1. The legacy `automate.py` reads all records into memory and caps exports at 250,000 rows. The new worker exporter streams CSVs and partitions workbook sheets.
2. The processor has file-level recovery, not durable row-offset checkpoints. The queue records durable job states, but interrupted files still restart from their beginning.
3. SQLite is retained only for local single-user metadata. Cloud tenancy, signed object URLs, production authentication and RLS are **PLANNED**, not asserted as present.
4. No supplied V4 source was found. The console calls `StandaloneEngineAdapter`, never calls its results canonical V4 output.

