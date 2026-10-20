# Director acceptance report — 20 October 2026

## Verified today

- Source backup and full local Git history bundle were created before code changes.
- The FastAPI local health endpoint started successfully.
- The completed local suite is `50 passed, 2 skipped`.
- A reconstructed synthetic source-to-engine-to-export acceptance processed 100 rows and produced 21 Lakhotia rows with a persisted filter-plan manifest.
- The local UI now implements two visibly distinct paths: **AI-Assisted Pipeline** and **AI Direct**. The first supports a nested, server-validated filter builder and bounded preview; the second supports profile objective selection and explicit plan approval.
- The fresh-install dependency typo was corrected from `httpx2` to `httpx`.

## Partially completed

- Browser E2E click-through is not executed by this environment. JavaScript syntax and server contracts are verified.
- Fourth-client behavior is tested through a synthetic configurable profile API test; it is not a new hard-coded default profile.

## Blocked or intentionally not done

- No cloud deployment, external provider call, private-record transfer, CRM/Supabase/Render modification, or GitHub operation was performed.
- 500k and 2.5m benchmarks are not tested. No three-crore capacity assertion is made.
- The second backup copy is separate locally but not on another physical device.

## Rollback

Restore the pre-change source with `git switch codex/audience-api-v1-contract` or recover from the artifacts recorded in `MAYUR_BACKUP_MANIFEST.json`.
