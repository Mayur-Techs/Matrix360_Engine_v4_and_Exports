# Render deployment: private pilot

This repository includes `render.yaml` for a **single-tenant private pilot**. It starts the FastAPI console and worker together in one Docker service and persists local SQLite metadata, uploads and exports on one attached disk. It is deployable, but it is deliberately not described as a multi-tenant production SaaS.

**19 October cloud gate:** this Blueprint is a reference only. No Render workspace has been selected and no service was created or deployed in this branch. The requested 512 MB web-service constraint is unsuitable for the V4 spreadsheet worker and must not be used for multi-million-row processing. The approved target design is a low-memory gateway plus private object storage, queue messages and independently sized worker jobs.

## What you need

1. A Render account connected to the Matrix360 GitHub repository.
2. A **paid Web Service compute plan**. Start at `1c-2g` (1 CPU / 2 GB RAM) because a processing worker shares that instance with the web console. Do not use the free plan for confidential client uploads or larger spreadsheets.
3. A 10 GB persistent disk, which is declared by `render.yaml`.
4. A strong administrator password and a private GitHub repository.
5. The existing OpenAI API key only if the optional header-only label assistant is required. It is entered as a Render secret, never committed.

## Simple deployment

1. Push the current repository, including `render.yaml`, to the Matrix360 GitHub repository.
2. In Render, choose **New → Blueprint**, select that private repository, and approve the proposed `matrix360-private-pilot` service.
3. During creation, enter values for `MATRIX_LOCAL_USERNAME`, `MATRIX_LOCAL_PASSWORD`, `MATRIX_LOCAL_TENANT_ID`, and—only if wanted—`OPENAI_API_KEY`. Render generates `MATRIX_SESSION_SECRET` automatically.
4. Deploy. Wait until the service health check reports `/healthz` as healthy.
5. Open the service URL, sign in, and upload a small synthetic file before any real client data.

## Security boundary

- Keep the repository private and use a long unique password.
- Use the `OPENAI_API_KEY` only for the explicit schema-label button. That call transmits non-contact headers only; it never transmits records or sample values.
- Do not claim this pilot is multi-tenant, horizontally scalable, or appropriate for public self-service customer accounts.
- Do not enable record-level AI review without a documented PII-transfer, retention and spend approval.

## Before a public SaaS launch

Replace the local adapters with managed Postgres plus row-level tenant isolation, private object storage and signed downloads, a durable job queue, malware scanning, authenticated user management, deletion/retention controls and independent worker scaling. An attached disk restricts the pilot to one instance, so it cannot provide high availability or horizontal scaling.

