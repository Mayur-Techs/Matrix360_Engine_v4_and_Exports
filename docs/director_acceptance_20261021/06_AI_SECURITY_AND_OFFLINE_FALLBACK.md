# 06 — AI safety, approval and offline fallback

Status: PASS for code/tested offline controls; CONFIGURATION REQUIRED for new live-provider testing.

- Mode A model boundary: objective plus eligible non-contact headers only.
- Mode B model boundary: selected versioned profile metadata, objective and eligible non-contact headers only.
- Rows, names, email, phone and address are excluded from model context by code and mock-provider tests.
- Direct identifier patterns are rejected before a provider request. Provider output is constrained JSON and revalidated by the typed filter DSL; unsupported fields and numeric identifier comparisons are rejected.
- Both browser flows required explicit approval. A Direct approval persists plan hash, schema fingerprint and `user_confirmed` state; stale schema fingerprints are rejected by tests.
- Provider errors/disabled settings produce the visible `deterministic-schema-planner / local-schema-only` state. No paid provider request was made in this acceptance run.
- Provider usage is recorded only from a returned usage payload; no prices or billing claims are made.
- HMAC workspace binding, timestamp, nonce replay denial and path mismatch are covered by `tests/test_service_gateway_auth.py`.

Security history check: tracked history has only expected key-variable references in `.env.example` and legacy configuration code; no project-key or generic key-shaped tracked blob was found. `.env.local` is ignored and not read. **ROTATION REQUIRED:** a credential previously pasted into chat must be rotated by the authorized account owner.
