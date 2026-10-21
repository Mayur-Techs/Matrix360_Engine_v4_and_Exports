# 01 — Source baseline and backup

Status: PASS (local preservation); PARTIAL (off-device recovery).

- Repository root: `C:\Users\MAYUR\Downloads\Matrix360_Engine_v4_and_Exports`
- Baseline commit present: `9a4da00143339ef9aa40f7454a20f5b593ed4292` (`Connect bounded AI planning pipelines`).
- Acceptance branch: `codex/mayur-director-acceptance-20261021`, created locally from that commit. No fetch, push, fork, PR, merge or deployment occurred.
- Baseline runtime: Python 3.12.14, Node 22.22.0, npm 10.9.4, Git 2.54.0.windows.1.
- Pre-existing untracked directories were preserved untouched: `.bench-director/`, `.release-checkouts/`, `backups/`.

## Existing recovery artifacts verified

| Artifact | SHA-256 | Verification |
| --- | --- | --- |
| `backups/private/MAYUR_V4_SOURCE_BACKUP_20261020.zip` | `95ACDA3682FB8FCFAF41CFB8B754E02BC7CB1ABAEDDC1AEC1C51C8440B266128` | Hash read successfully |
| `backups/private/MAYUR_V4_OFFLINE_GIT_BACKUP_20261020.bundle` | `CEE141547BB9C489C4EE1D1EC9EF706B815B7E7B962C064801824608406DE05B` | `git bundle verify` passed; complete history reported |
| `backups/offline/*SECOND_COPY*` | Same hashes as the private copies | Hashes match |

Limitation: both copies are on the same workspace disk. They are useful local recovery artifacts, not independent off-device disaster recovery. No source archive was opened or restored over the working tree because that would be destructive.

## Inventory

- API/control plane: `services/api/`
- Separate worker and export generation: `services/worker/`
- V4 rule engine: `matrix_engine/engine/`
- Browser console: `apps/web/`
- Contract, security, filter, numeric and acceptance tests: `tests/`
- Versioned Avinash handoff draft: `docs/integrations/`

The tracked `.env`/`.env.local` paths were checked without reading values; `.env.local` is ignored and not tracked. A prior key pasted into chat is **ROTATION REQUIRED** and is not reproduced in this package.
