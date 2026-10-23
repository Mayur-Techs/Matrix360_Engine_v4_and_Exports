# Audience Intelligence integration handoff — v1

## Ownership and boundary

Avinash owns the only client-facing UI, Supabase identity, workspace choice, browser session and CRM ingestion. This repository owns data processing and never becomes a customer destination. Pratha and Tanmayi are not connected.

## Required service-to-service gateway

1. Browser calls Avinash's authenticated backend; it never calls this local API directly and never supplies a tenant ID.
2. Avinash validates its Supabase session and membership, maps it to one workspace, and signs each gateway request with the server-only MATRIX_SERVICE_AUTH_SECRET.
3. The CRM sends X-Matrix-Workspace, X-Matrix-Timestamp, X-Matrix-Nonce and X-Matrix-Signature. The signature covers v1, HTTP method, request path, workspace, timestamp and nonce. The audience gateway verifies the signature, a five-minute expiry, a single-use nonce and workspace binding before mapping the workspace to its own tenant key. Reject absent, expired, replayed and mismatched requests.
4. The gateway returns only that workspace's datasets, jobs, results and signed export references. CRM ingestion is idempotent by `(workspace_id, audience_lead_id, job_id)` and marks records **research fit**, never consent or sales qualification.

Local V4 accepts a local owner cookie for development only. In cloud mode, the CRM secret belongs only in the two server environments; it is never returned in a browser response, repository or client-side configuration.

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

## V5 Engine capabilities available to Avinash

1. **Zero-Hardcode Semantic Alias Agent (/api/v1/v5/schema/resolve)**:
   - 3-Layer resolution: expanded ontology (25+ synonyms/field including Indian business aliases), content fingerprinting (GSTIN, vehicle registration, ₹ / Cr / Lakh currency), and self-learning alias store (learned_aliases.json).
   - Resolves unstructured datasets without manual column remapping or SCHEMA_REVIEW_REQUIRED blocks.

2. **Universal Dynamic Brand Qualifier (/api/v1/v5/qualify/lead)**:
   - Scores leads for ANY client profile across India (not limited to 3 hardcoded clients).
   - Generates composite scores (0-100), affluence / vehicle pricing tier estimation, and transparent reasoning summaries for CRM lead review.

3. **Multi-Choice Company Filter Generator (/api/v1/v5/filters/company)**:
   - Translates natural audience prompts into structured sector, turnover, decision-maker, and affluence asset choices.

4. **Dual Google Drive Cloud Bridge (/api/v1/v5/dual-drive/manifest)**:
   - Prepares deterministic sync manifests mapping local artifacts to Avinash output Google Drive folders with 0MB persistent storage impact on compute instances.
