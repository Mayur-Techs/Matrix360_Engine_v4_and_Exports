# Matrix 360 — Director acceptance report (21 October 2026)

## Decision

Local controlled acceptance: **PARTIAL / READY FOR DIRECTOR REVIEW**. The isolated synthetic browser workflows, worker, exports, persistence, safety controls and repaired Parquet path pass. This is not approval for production deployment, hosted integration, real-data processing or public SaaS launch.

## What changed

- Added actual Parquet worker support and a regression test.
- Corrected tablet-width filter-editor overflow without changing the workflow or API.
- Updated the dynamic-profile acceptance fixture to a fictional Safety Equipment business.

## Evidence

- Baseline: 54 passed, 2 skipped before this acceptance change.
- Final suite: 55 passed, 2 documented Windows-sandbox skips after the Parquet regression was added.
- Targeted repaired-path/security checks: 16 passed; security subset: 7 passed.
- Real browser Mode A: 21 of 100 synthetic rows under a four-condition approved plan.
- Real browser Mode B: 23 of 100 synthetic rows under its intentionally broader approved plan.
- Real downloads, workbook reopen and local restart persistence were exercised.
- P1 measured benchmark: 25,000 synthetic rows in 13.750s, reconciled true.

## Required Director gates

- Rotate the prior chat-exposed credential.
- Approve a bounded live-provider test only if needed.
- Approve hosted environment, billing, security, data retention and rollback before any deployment.
- Provide safe valid XLS/XLSB fixtures before claiming those formats are acceptance-tested.

See files `01_` through `10_` in this directory for reproducible detail.
