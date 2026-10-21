# 08 — Release quality and risks

Status: PARTIAL — local controlled acceptance evidence is ready; public SaaS release is not approved.

Fixed in this acceptance branch:

1. Parquet upload inspection and processing had diverged. The engine now streams Parquet row batches and has an end-to-end regression test.
2. Tablet filter controls caused document-level horizontal overflow at 768px. They now stack at the tablet breakpoint; 390px, 768px and 1440px final checks have no page overflow.

Known gates:

- Local SQLite/filesystem/single-owner auth are not multi-tenant SaaS controls.
- Valid XLS/XLSB fixtures still need execution proof.
- A real provider call is not current acceptance evidence and requires bounded spend approval.
- Malware scanning, real auth/RLS, private object storage, signed downloads, retention/deletion, durable queue/recovery and independent worker scale remain production work.
- The core restarts an interrupted source file from the beginning; it is not row-level resumable.
- No hosted deployment, migration, GitHub push or CRM/Supabase integration has been performed.
