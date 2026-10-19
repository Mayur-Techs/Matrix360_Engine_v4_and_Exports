# Audience Intelligence integration handoff — v1

## Ownership and boundary

Avinash owns the only client-facing UI, Supabase identity, workspace choice, browser session and CRM ingestion. This repository owns data processing and never becomes a customer destination. Pratha and Tanmayi are not connected.

## Required service-to-service gateway

1. Browser calls Avinash's authenticated backend; it never calls this local API directly and never supplies a tenant ID.
2. Avinash validates its Supabase session and membership, maps it to one workspace, and sends a short-lived signed service assertion to the audience gateway.
3. The production gateway verifies signature, issuer, audience, expiry, nonce and workspace binding before mapping the workspace to its own tenant key. Reject absent, expired, replayed and mismatched assertions.
4. The gateway returns only that workspace's datasets, jobs, results and signed export references. CRM ingestion is idempotent by `(workspace_id, audience_lead_id, job_id)` and marks records **research fit**, never consent or sales qualification.

Local V4 accepts a local owner cookie for development only. It must not be exposed as this protocol.

## Frontend sequence

`Upload -> schema-catalog -> client profile -> filter-plans/suggest -> validate -> preview -> apply -> jobs -> status/results -> exports -> CRM ingest reference`.

Render nested groups literally. A group such as `all(geo, any(industry A, industry B), present(phone))` must visually retain its parentheses. Only source columns returned by `schema-catalog` are selectable. `suggest` is intentionally a schema-only deterministic fallback until a model adapter and data-transfer approval are in place.

## Security/PII constraints

- Send neither rows, contact values nor raw addresses to a model provider. The existing header-label endpoint sends only eligible column names after a user click.
- Phone source remains a string; do not coerce it to numeric values or scientific notation.
- Vehicle attributes are observed fields only, never evidence of wealth, interest, consent or eligibility.
- Treat unknown permission as unknown. Exports are not outreach authorization.

## Contract evidence

- OpenAPI summary: `docs/integrations/audience-api-v1.openapi.yaml`
- Filter schema/evaluator: `services/api/filter_dsl.py`
- Synthetic fixture generator: `scripts/seed_synthetic.py`
- Local contract tests: `tests/test_filter_dsl.py`, `tests/test_advanced_filters.py`, `tests/test_acceptance_exports.py`

## Cloud handoff gate

Do not connect a real Supabase workspace, create storage buckets, or deploy a worker until the Director selects a project, approves a staging-only scope and accepts cost/security changes. The known connected projects are not implicitly authorized targets.
