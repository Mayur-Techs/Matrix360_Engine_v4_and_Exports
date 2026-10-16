# Security threat model — local pilot

## Boundaries

| Boundary | Current control | Residual risk |
| --- | --- | --- |
| Browser to API | Same-origin httpOnly, SameSite session cookie; no query-string token | Local HTTP is for loopback development only; production HTTPS/CSRF policy remains required |
| Upload | Extension allow-list, filename/path sanitisation, byte limit, streamed disk write | No antivirus/content scanner or cloud multipart resume yet |
| Tenant metadata | Tenant scope on every API lookup and export download | SQLite local mode has one tenant; multi-tenant RLS is not implemented |
| Worker | Separate process and job state in SQLite | File-level rather than row-offset recovery; cancellation is not yet cooperative mid-file |
| Spreadsheet exports | String values are prefixed when starting with `=`, `+`, `-` or `@` | User should still open exports only in trusted tools |
| AI | Key is server-side, ignored by Git and unused by default | Approval and a PII-minimisation review are required before enabling it |

## Abuse cases tested

- **VERIFIED:** unauthenticated dataset listing receives HTTP 401 in `tests/test_local_flow.py`.
- **VERIFIED:** unsupported `.exe` upload receives HTTP 415.
- **VERIFIED:** export download checks the session tenant and uses an opaque export ID, never a URL bearer token.
- **UNVERIFIED:** real cloud cross-tenant denial, object-storage URL expiry, CSRF under a production host and malware scan integration.

## Release gate

Do not host real client data until production authentication, HTTPS, Postgres/RLS, private object storage, short-lived signed downloads, scan policy, rate limiting, retention/erase workflow and tenant-denial tests are implemented and reviewed.

