# 02 — Baseline and test inventory

Status: PASS.

Initial baseline before this acceptance change set:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings --maxfail=1 --basetemp .test-tmp-director-baseline
```

Result: `54 passed, 2 skipped in 16.54s`. The two skips are deliberate Windows desktop-sandbox socket restrictions in `tests/test_local_flow.py`; the real loopback Uvicorn/browser acceptance path was run instead.

Other baseline checks passed:

```powershell
node --check apps\web\app.js
.\.venv\Scripts\python.exe -m compileall -q services matrix_engine
git diff --check
```

The final suite count increases by one because this acceptance work adds `tests/test_parquet_processing.py`, an end-to-end regression for the repaired Parquet worker path. Final result: `55 passed, 2 skipped in 9.98s`. The raw final log is `FINAL_PYTEST_LOG.txt` in this directory.

Local launch used only `127.0.0.1:8041`, an isolated synthetic `MATRIX_STORAGE_ROOT`, a synthetic local operator, and `MATRIX_AI_PIPELINE_ENABLED=false`.
