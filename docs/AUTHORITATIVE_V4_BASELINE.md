# Authoritative V4 baseline

Audited: 16 October 2026.

The authoritative implementation in this delivery is the supplied, executable local V4 engine:

- `matrix_engine/engine/core.py` — bounded-memory ingestion, source preservation, geography and reconciliation.
- `matrix_engine/engine/targeting.py` — the configuration-driven three-client rules, currently version `4.1.0`.
- `services/worker/adapter.py` — the sole application boundary that invokes that engine.

## Branch comparison result

The local repository has one supplied baseline commit and its configured GitHub remote had no published heads when audited. There are no local or remote branches dated 15 October 2026, so an October-15 branch comparison cannot be performed or claimed. No supplied source was discarded: the V4 engine remains in place and the console calls it through the adapter.

## Consolidation rule

Only reusable source, tests, configuration templates and documentation belong in the release repository. Client uploads, generated exports, browser artifacts, runtime databases, logs and local credentials remain local and are excluded by `.gitignore`.
