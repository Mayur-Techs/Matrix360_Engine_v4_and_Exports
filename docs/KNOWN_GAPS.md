# Known gaps

- **CONSTRAINED:** the supplied V4 engine is authoritative for this repository. No 15-October branch, v2.1/v2.2 package or old console POC was supplied, so compatibility with those unavailable artifacts cannot be claimed.
- **PLANNED:** cloud authentication provider, RLS, signed object-storage downloads, multipart resumable cloud upload, malware scanning and production retention controls.
- **PLANNED:** durable row-level checkpoint/replay and background export for very large Excel output. The current worker has durable job states but the reused core restarts an interrupted input file.
- **PLANNED:** verified benchmarks on this machine at 100,000 and 500,000 rows. No historical benchmark is treated as current verification.
- **REQUIRED APPROVAL:** enter an OpenAI API key locally and approve PII transfer and a bounded AI budget before any live AI request.

