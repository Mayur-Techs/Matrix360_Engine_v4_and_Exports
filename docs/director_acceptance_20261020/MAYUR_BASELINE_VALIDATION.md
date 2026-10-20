# Mayur V4 baseline validation — 20 October 2026

Baseline commit before this acceptance cycle: `54a1d2f311fde67ee68d6c0c22c7da28e831be32` on `codex/audience-api-v1-contract`.

## Verified locally

- FastAPI started on loopback port 8031 and `/healthz` returned `status: ok`, `mode: local-single-user`, and engine V4 rulebase identity.
- Local ignored `.env` was not printed or archived. Its presence means an optional header-only schema provider can be configured, but no external AI call was made in this cycle.
- The full automated suite before implementation was `49 passed, 2 skipped`.
- Required API modules and tests listed in the Director directive are present locally.
- CSV/XLSX/XLS/XLSB/TSV/Parquet/JSONL support is implemented by the existing engine. This cycle did not manually exercise each binary format; that part is **NOT TESTED** beyond the existing automated coverage.

## Corrected baseline defect

`requirements.txt` referenced the non-existent package `httpx2`. It now declares `httpx>=0.27,<1`, which matches the installed TestClient dependency and prevents a fresh local install from failing.

## Local operation

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000
```

Start the worker in a second PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m services.worker.runner --interval 1
```

Open `http://127.0.0.1:8000`. Use only synthetic data for Director demonstration.
