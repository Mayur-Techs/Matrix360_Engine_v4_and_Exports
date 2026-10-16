# Matrix 360 Standalone Data Engine 3.0

This is a new implementation based on the supplied requirements. Previous v2.2 source was not available locally or located by the filename search; this package is not a verified patch of that code. It operates independently of Pratha.

## Run locally
Python 3.12 recommended. In this directory:

    python -m venv .venv
    # Windows: .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m pytest -q tests
    python -m engine.core --input /path/to/source_folder --workspace /path/to/separate_workspace

Input and workspace must be separate, non-nested directories. Re-running skips unchanged files. Modified sources replace active versions; source removal deactivates old records. Failed replacements are excluded rather than silently serving stale results. Original files remain unchanged. CSV/Parquet contain personal data: restrict the workspace to authorized operators.

## Drive folder URL

    python -m engine.drive --url https://drive.google.com/drive/folders/FOLDER_ID --cache /path/to/cache --workspace /path/to/workspace

Set MATRIX_DRIVE_ACCESS_TOKEN privately in the process environment to a valid user-authorized Google Drive read-only OAuth access token. Never put it in source code. This is a standalone application: the ChatGPT Google Drive connection does not grant the downloaded program credentials. Token provisioning and refresh are not implemented. Do not run multiple sync commands against the same cache. The adapter implements recursive pagination, retry, checksum/size checks and incremental downloads, then builds the current source snapshot. Failed downloads stop the run. Non-native binary files are supported; Google-native files and shortcuts require future adapters. Drive read-only operations only: no sharing, marketing messages, advertising uploads, or publishing.

## Implemented

- Streaming CSV/TSV/XLSX/XLSM, legacy XLS, XLSB and JSONL readers (XLS uses xlrd and may use significant memory).
- Conservative configurable-in-code field aliases; unknown schemas enter failed/review status.
- Headerless email-sheet handling; original row/field values, SHA256 source version and stable source record IDs.
- Format validation (not deliverability or identity verification), explicit geography evidence and uncertainty.
- DuckDB persisted records, versioned Parquet shards, SQLite file job ledger; atomic shard replacement and process lock.
- Contact collision review groups; no automatic identity merge.
- Independent three-project P2 research rules; Q1/Q2/P1 are not assigned without verified evidence.
- Separate HOLD fields for WhatsApp, Instagram and referral activation; no consent inference.
- Full source-row reconciliation, reports and CSV exports.

## Important limitations

This is a tested engineering build, not all previously discussed product features. JSON arrays, XML, password-protected documents, ZIP/RAR extraction, fuzzy entity resolution, comprehensive geography, configurable profile UI, authenticated browser interface, tenant isolation, token refresh and hosted scheduled execution remain unimplemented. These formats fail explicitly. Full 30-million-row processing has not been tested. File restart reprocesses an interrupted file from its beginning; it is not row-offset resume. Old Parquet shards are retained for audit and need a retention policy. Duplicate emails/phones are review signals, not proof of the same person. Logs may include source filenames; protect job reports too.

## Evidence from this run

The ChatGPT connected Drive listed 69 immediate items at the supplied root. The complete 9896 (1) subfolder contained one workbook; downloaded and processed all 9,896 nonblank records. Sheet2/Sheet3 were empty. Larger Business Owners XLSX and Car-Owner-Data XLSB fetches failed with connector transport errors; those datasets were NOT processed. Root listing is not a complete recursive inventory.

The attached master workbook supplied a separate 10,054-record source ledger. Only that ledger was ingested, avoiding double counting its derived tabs. The final lead workbook retains the user's existing 4,053 research assignments across 3,882 source contacts and clearly labels their provenance. It does not present those candidates as discoveries from the vehicle folder. All 10,054 reference contacts have UNKNOWN consent. Empty eligible tabs are intentional.

Outputs: jobs.sqlite, warehouse.duckdb, versioned Parquet, all_records.csv, wb_research_leads.csv, contact_collisions.csv, report.json. Raw CSV is intended for programmatic processing: import columns as text in spreadsheet tools. The delivered XLSX stores strings literally to prevent formula execution.
