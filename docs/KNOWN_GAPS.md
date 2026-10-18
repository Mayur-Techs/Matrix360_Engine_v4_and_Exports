# Known gaps

- **CONSTRAINED:** the supplied V4 engine is authoritative for this repository. No 15-October branch, v2.1/v2.2 package or old console POC was supplied, so compatibility with those unavailable artifacts cannot be claimed.
- **PLANNED:** cloud authentication provider, RLS, signed object-storage downloads, multipart resumable cloud upload, malware scanning and production retention controls.
- **PLANNED:** durable row-level checkpoint/replay and background export for very large Excel output. The current worker has durable job states but the reused core restarts an interrupted input file.
- **PLANNED:** verified benchmarks on this machine at 100,000 and 500,000 rows. No historical benchmark is treated as current verification.
- **CONSTRAINED:** the optional header-only schema assistant cannot inspect rows or values. It only improves labels/grouping and cannot change classification or export logic. Record-level AI review remains disabled unless a separate PII-transfer and spend approval is documented.

