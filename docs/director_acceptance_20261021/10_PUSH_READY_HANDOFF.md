# 10 — Push-ready handoff

Status: LOCAL ONLY.

This branch is prepared for review as `codex/mayur-director-acceptance-20261021`. It has no remote write. Before any authorized future push, the owner should:

1. Rotate the previously chat-exposed credential and update only the approved secret store.
2. Review this acceptance package and local artifact manifest.
3. Re-run the full suite and a synthetic browser smoke test on the intended staging environment.
4. Validate XLS/XLSB with lawful synthetic fixtures.
5. Obtain Director approval for hosted infrastructure, data retention, identity/RLS, cost limits and rollback.

Do not include `output/`, `.playwright-cli/`, runtime databases, `.env`, `.env.local`, real datasets, backups, or browser sessions in a shareable source archive.
