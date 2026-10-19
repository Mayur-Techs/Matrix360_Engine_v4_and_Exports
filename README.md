# Matrix 360 / Audience Intelligence

Local, evidence-bound audience-data processing console. It deliberately operates independently of the Pratha, Tanmayi and Avinash systems.

## Current truth

- **VERIFIED by source inspection:** `matrix_engine` contains a documented V4 rule implementation (formerly labelled 4.0.0) using streaming file readers, Parquet and DuckDB. The aligned local rules are now version `4.1.0`.
- **Scope boundary:** this delivery is an independent local implementation; it does not assert compatibility with an unavailable older v2.x package or former console POC.
- **Local mode:** FastAPI console + separate worker + SQLite metadata + local storage. It is for one local tenant only, not a cloud security claim.
- **AI:** deterministic classification is always authoritative. The ignored root `.env` can hold an `OPENAI_API_KEY`; a user-triggered schema assistant can send only non-contact column headers to `gpt-4o-mini` to improve display labels. An explicitly enabled, call-capped research review sends only company, sector, district and geography status, records review suggestions separately, and cannot alter a deterministic classification or export.

## Run locally (Windows PowerShell)

```powershell
Copy-Item .env.example .env
# Edit .env: set a strong MATRIX_LOCAL_PASSWORD; leave OPENAI_API_KEY blank unless approved.
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000
```

In a second PowerShell window from this repository:

```powershell
.\.venv\Scripts\Activate.ps1
python -m services.worker.runner --interval 1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Sign in with the local values in `.env`, upload a safe synthetic file from `python scripts/seed_synthetic.py`, select it, and start a job. The worker will create the three CSVs, a combined XLSX, and a JSON manifest. Do not upload client-sensitive data to an unauthenticated or public instance.

For a director-operated local console, Docker starts the API and worker together. After the one-time administrator start command, all upload, filtering, job monitoring and downloads occur in the browser; no terminal commands are needed by the director.

## Director workflow

1. Open **Audience data**, choose a file or folder, then select **Upload & inspect**.
2. Open **Import & process**, select the uploaded dataset, and click **Start processing**. The V4 worker automatically runs the classification pipeline.
3. Use **Jobs & logs** for live status and a downloadable job log; use **Exports** for the generated client CSVs, combined workbook, and manifest. **Governance log** has its own downloadable audit log.

## Docker local mode

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Docker binds to `127.0.0.1` only. When `OPENAI_API_KEY` is present in the ignored `.env`, it is passed only to the API container for an explicit, header-only schema-label request; it is never committed or displayed. The named Docker volume holds the local metadata, uploads and exports. It is not an approved shared or cloud-production persistence design.

## Checks

```powershell
python -m pytest -q
python -m compileall -q services matrix_engine/engine
```

## API

The OpenAPI document is available at `/openapi.json` and interactive local docs at `/docs`. Core endpoints are versioned under `/api/v1`: session login, datasets, jobs, results, exports and audit. Requests require the session cookie; no bearer token is placed in a URL.

## Security and deployment

Read [docs/EXISTING_CAPABILITIES_AUDIT.md](docs/EXISTING_CAPABILITIES_AUDIT.md), [docs/ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md), and [docs/KNOWN_GAPS.md](docs/KNOWN_GAPS.md) before treating this as a pilot candidate. In particular, production needs a real auth provider, Postgres/RLS, private object storage and signed downloads.

The [V4 alignment audit](docs/V4_ALIGNMENT_AUDIT.md) records the verified implementation, the West Bengal filter behaviour, and the remaining production gates.

## Render private-pilot packaging

`render.yaml` packages a one-instance, single-tenant private pilot: one Docker service runs the API and worker, while an attached disk retains its SQLite metadata, uploads and exports. It is not horizontally scalable or approved as a multi-tenant public SaaS. Follow [docs/DEPLOY_RENDER.md](docs/DEPLOY_RENDER.md) for the concise, operator-led deployment checklist.

