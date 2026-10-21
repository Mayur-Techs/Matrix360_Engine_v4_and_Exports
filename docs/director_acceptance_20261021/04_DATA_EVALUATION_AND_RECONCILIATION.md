# 04 — Synthetic data evaluation and reconciliation

Status: PASS for CSV/XLSX/JSONL/NDJSON/Parquet paths exercised by tests; PARTIAL for valid XLS/XLSB fixture execution.

## Evaluated file

- File: `docs/director_acceptance_20261020/synthetic_acceptance/director_synthetic.csv`
- Synthetic rows: 100
- SHA-256: `A5F68D99636EB191CCF9237E37CB1C2D0C41D675195162F4FF0F250F49A6DD24`
- Mode A approved-plan preview and completed Lakhotia export: 21 rows.
- Mode B approved-plan result: 23 rows.

The file contains purposeful boundary and quality cases, including a below-threshold turnover, an invalid turnover, a missing district and an outside-West-Bengal row. The engine preserves source file/sheet/row provenance and reason codes; it does not silently merge collision groups.

## Reconciliation

For each completed worker run: `active_rows == expected_rows`; Mode A processed 100 input rows with 99 `WB_CONFIRMED` and 1 `OUTSIDE_WB`. The filter result is a subset of the active source, not an ingestion count. `Unique_export_candidates` was 21 for Mode A and 23 for Mode B.

## Format status

| Format | Status | Evidence |
| --- | --- | --- |
| CSV, TSV | PASS | Engine reader and real browser CSV run |
| XLSX, XLSM | PASS | Upload-inspection regression covers worksheets; OpenPyXL is installed |
| JSONL, NDJSON | PASS | Regression covers schema and malformed NDJSON with no invented headers |
| Parquet | PASS | New worker end-to-end test processes 2 synthetic rows; this repaired an API/worker mismatch |
| XLS | CONFIGURATION REQUIRED | Reader and `xlrd` are installed, but no safe valid XLS fixture/writer was present |
| XLSB | CONFIGURATION REQUIRED | Reader and `pyxlsb` are installed, but no safe valid XLSB fixture/writer was present |

Malformed NDJSON has a tested `failed` inspection with empty headers/filter fields. Missing registered exports are tested as unavailable and return a safe 404 rather than a dead download path.
