# Mayur local API handoff — future Avinash integration

Status: **local contract verified; no live integration performed**.

The stable handoff contract is documented in `docs/integrations/AVINASH_AUDIENCE_HANDOFF.md` and `docs/integrations/audience-api-v1.openapi.yaml`.

- Browser traffic must go to Avinash's authenticated backend, never directly to the Mayur service.
- The backend signs method, path, workspace, timestamp, and nonce with the server-only service secret.
- Mayur verifies the five-minute expiry, nonce single use, signature, and workspace mapping before enforcing tenant scope.
- The local regression suite covers signature path binding and nonce replay rejection in `tests/test_service_gateway_auth.py`.
- Filter plans are schema-bound and must be passed through validate/preview/apply before job execution.

No Avinash CRM, Supabase project, Render service, GitHub remote, secret, browser configuration, or production environment was changed in this workstream.
