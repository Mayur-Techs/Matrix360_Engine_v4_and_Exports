# Release status — 16 October 2026

## Implemented

- Local FastAPI console with cookie session, native multi-file/folder controls, streamed upload, schema sample, job queue UI, audit list, results table and exports.
- Separate persistent local worker, SQLite metadata, DuckDB-backed results query, legacy-processor adapter, formula-safe streamed CSVs and partition-aware combined workbook.
- Versioned JSON-schema contracts, client configuration and local Docker Compose.

## Verified

- `python -m pytest -q`: automated regression suite passes; socket-bound HTTP tests are intentionally skipped in the Windows desktop sandbox and are covered by a live Uvicorn smoke test.
- Authenticated synthetic local flow: upload → queue → worker → 4 rows → 5 protected exports: **passed**.
- Browser: local login and dashboard with no browser-console errors: **passed**. Screenshot: `output/playwright/matrix360-local.png`.

## Not released

No cloud environment was provisioned and no public URL exists. The supplied V4 rule engine is present and is the authoritative local baseline; see [AUTHORITATIVE_V4_BASELINE.md](AUTHORITATIVE_V4_BASELINE.md). Private client data remains local and is never committed or sent to AI by default. See `KNOWN_GAPS.md` before any cloud release decision.

