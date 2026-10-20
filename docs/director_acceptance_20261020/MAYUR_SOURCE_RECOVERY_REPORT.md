# Mayur V4 source recovery report — 20 October 2026

## Preserved baseline

- Local branch: `codex/audience-api-v1-contract`
- Current source commit: `54a1d2f311fde67ee68d6c0c22c7da28e831be32`
- Tracked source files: 89
- Recovery source: local Git working tree and all local Git refs; no remote access was used.

The expected V4 files are present in the local checkout: `services/api/audience_plan.py`, `services/api/filter_dsl.py`, `services/api/numeric_values.py`, `services/api/schema_intelligence.py`, `services/api/app.py`, `tests/test_ai_direct_plan.py`, and `tests/test_numeric_filter_contract.py`.

## Preservation actions

1. Created a shareable source archive from tracked files only. It excludes ignored `.env`, runtime data, private datasets, historic exports, and untracked files.
2. Created a Git bundle from every local ref, preserving commit history and the local stash.
3. Copied both artifacts to a second local directory before implementation work began.

## Restore procedure

To inspect the preserved source, unpack `MAYUR_V4_SOURCE_BACKUP_20261020.zip` into a new directory. To recover history, run `git clone MAYUR_V4_OFFLINE_GIT_BACKUP_20261020.bundle recovered-mayur-v4` from the backup directory, then verify the SHA-256 checksum in `MAYUR_BACKUP_MANIFEST.json`.

## Limitation

The independent copy is in a separate local directory on the same Windows volume. It protects against accidental project-folder modification but is not off-device disaster recovery. No other writable/offline destination was available in this execution environment.

## Untouched material

The pre-existing `.release-checkouts/` directory is untracked and was not changed. Original input datasets, runtime outputs, historic exports, and the local Git history were not modified.
