# AI-Assisted Pipeline acceptance

## Implemented

The local browser now exposes **AI-Assisted Pipeline**. It uses the existing `/api/v1/datasets/{id}/ai-direct/plan`, `/filter-plans/preview`, `/filter-plans/apply`, and `/jobs` endpoints rather than duplicating filtering in JavaScript.

- A prompt generates a schema-bound plan from objective text and actual imported headers.
- The editor renders explicit nested `ALL`, `ANY`, and `NOT` groups; conditions can be added, removed, and nested.
- Numeric comparisons are only offered for fields marked numeric-eligible by upload inspection.
- `BETWEEN` is presented as inclusive; `present` and `empty` have no value input.
- Edited plans must pass server validation and a bounded preview before approval. A valid approved plan is persisted before job creation and is executed by the normal worker/exporter.
- The UI labels the deterministic provider honestly as `RULE-BASED PLANNER — MODEL NOT CONNECTED` when that provider is returned.

## Verified

The server-side nested DSL/numeric/export contract is covered by `tests/test_numeric_filter_contract.py`, `tests/test_advanced_filters.py`, and the reconstructed Director acceptance test.

Browser click-through E2E: **NOT TESTED**. JavaScript syntax was checked with Node; no fabricated browser result is claimed.
