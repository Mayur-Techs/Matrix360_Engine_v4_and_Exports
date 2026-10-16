# Schema and API contracts

## API versioning

All browser and programmatic endpoints use `/api/v1`. The local OpenAPI document is exposed at `/openapi.json` when the API runs.

| Area | Endpoint |
| --- | --- |
| Session | `POST /api/v1/auth/login`, `GET /api/v1/auth/session`, `POST /api/v1/auth/logout` |
| Data | `POST /api/v1/datasets`, `GET /api/v1/datasets` |
| Jobs | `POST /api/v1/jobs`, `GET /api/v1/jobs`, `GET /api/v1/jobs/{id}` |
| Results | `GET /api/v1/jobs/{id}/results?offset=&limit=&search=&geo_status=&geo_statuses=&districts=&client_profiles=` |
| Export | `GET /api/v1/jobs/{id}/exports`, `GET /api/v1/exports/{id}/download` |
| Audit | `GET /api/v1/audit` |

## Local metadata contract

Every dataset, file, job, export and audit event has a `tenant_id` in local metadata. The local mode has exactly one configured tenant and is not a substitute for cloud RLS. Jobs use the states `queued`, `running`, `needs_review`, `completed`, `failed` and `cancelled`; only the first four are currently produced by the worker.

The exported-record and job-manifest schemas are versioned under `packages/contracts/`. Records preserve `source_record_id`, source file/sheet/row, geographic result, three independent client classes and rule version. `P2` means evidence-bound research fit only; it never represents permission or confirmed purchase intent.

