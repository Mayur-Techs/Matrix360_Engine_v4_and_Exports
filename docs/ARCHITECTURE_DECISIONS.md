# Architecture decisions

## ADR-001: Local-first pilot with a separate API and worker

**Decision:** use FastAPI for the local API/console and a separately launched Python worker consuming SQLite-backed job metadata. The legacy standalone engine remains the processing implementation behind `StandaloneEngineAdapter`.

**Why:** the supplied package already depends on DuckDB, Arrow and Python spreadsheet readers. Keeping compute out of the HTTP handler avoids request timeouts and permits a later Postgres/queue/object-store adapter without changing the API contract.

**Status:** accepted for local single-user demo. SQLite is not approved for multi-tenant cloud deployment.

## ADR-002: Browser console without a frontend framework migration

**Decision:** serve a small, same-origin static console from FastAPI rather than introducing a new Next.js toolchain into an export-only repository.

**Why:** this is the smallest reversible step that delivers native file/folder selection, real upload streaming, status polling and authenticated result review. A Next.js migration is **PLANNED** for the cloud pilot after the V4 source and design ownership are resolved.

## ADR-003: AI is opt-in and unavailable without an owner key

**Decision:** `OPENAI_API_KEY` is loaded only server-side from the ignored local environment. Jobs default to deterministic rules; the legacy AI helper can only make review suggestions and is not invoked by the worker.

**Why:** no API key was supplied, and the brief prohibits unapproved spending or uploading PII to a provider.

