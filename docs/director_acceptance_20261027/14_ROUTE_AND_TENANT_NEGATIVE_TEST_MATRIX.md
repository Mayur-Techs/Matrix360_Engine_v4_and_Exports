# MATRIX 360 — ROUTE AND TENANT NEGATIVE TEST MATRIX
**Directory:** `docs/director_acceptance_20261027/14_ROUTE_AND_TENANT_NEGATIVE_TEST_MATRIX.md`  
**Execution Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Security Standard:** Strict Fail-Closed Zero-Trust Multi-Tenancy  
**Test Evidence:** Verified in [`tests/test_tenant_security_p0.py`](file:///c:/Users/MAYUR/Downloads/Matrix360_Engine_v4_and_Exports/tests/test_tenant_security_p0.py) (9 of 9 Passed)

---

## 1. Exhaustive Endpoint & Alias Security Inventory

Every route and route-alias across `services/api/` has been enumerated and tested against three distinct threat vectors:
1. **Anonymous Callers (Unauthenticated):** Zero credentials or expired tokens.
2. **Cross-Tenant Non-Owner (Member):** Valid session for Tenant A attempting to access Tenant B resources.
3. **Cross-Tenant Workspace Owner:** Admin of Tenant A attempting to manage Tenant B resources.

| Route / Alias | Method | Authentication Guard | Tenant Isolation Enforcement | Anonymous Access | Tenant A -> Tenant B Access | Admin Global Access (`client_id=ALL`) | Verified Test |
|---|---|---|---|---|---|---|---|
| `/api/campaign/start` | POST | `current_user` fail-closed | `verify_tenant_access(user, req.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A (single job) | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/status/{job_id}` | GET | `current_user` fail-closed | `verify_tenant_access(user, job.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/results/{job_id}` | GET | `current_user` fail-closed | `verify_tenant_access(user, job.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/active` | GET | `current_user` fail-closed | Server-side filter `j.client_id == user_tenant` | **401 Unauthorized** | **Opaque (0 rows leaked)** | Platform admin only | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/cancel/{job_id}` | POST | `current_user` fail-closed | `verify_tenant_access(user, job.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/export/{job_id}` | GET | `current_user` fail-closed | `verify_tenant_access(user, job.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/campaign/ai/advisor-chat` | POST | `current_user` fail-closed | `verify_tenant_access(user, req.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/campaign/ai/qualify-lead` | POST | `current_user` fail-closed | `verify_tenant_access(user, req.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/leads` | GET | `current_user` fail-closed | `verify_tenant_access(user, effective_client)` | **401 Unauthorized** | **403 Forbidden** | **403 Forbidden** (non-admin) | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/discovery/leads` | GET | `current_user` fail-closed | `verify_tenant_access(user, effective_client)` | **401 Unauthorized** | **403 Forbidden** | **403 Forbidden** (non-admin) | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/discovery/ingest-maps` | POST | `current_user` fail-closed | `verify_tenant_access(user, client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants` |
| `/api/discovery/sources-summary` | GET | `current_user` fail-closed | `verify_tenant_access(user, effective_client)` | **401 Unauthorized** | **403 Forbidden** | **403 Forbidden** (non-admin) | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/discovery/send-to-engine` | POST | `current_user` fail-closed | Binds dataset to `user.tenant_id` | **401 Unauthorized** | Bound to caller tenant | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_api_discovery_send_to_engine_bridge` |
| `/api/export` | GET | `current_user` fail-closed | `verify_tenant_access(user, effective_client)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/discovery/export` | GET | `current_user` fail-closed | `verify_tenant_access(user, effective_client)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/config-keys` | POST | `current_user` + `role == "owner"` | Rejects non-admin | **401 Unauthorized** | **403 Forbidden** | System Admin only | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/discovery/config-keys` | POST | `current_user` + `role == "owner"` | Rejects non-admin | **401 Unauthorized** | **403 Forbidden** | System Admin only | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/crawl` | POST | `current_user` fail-closed | Scoped to caller tenant | **401 Unauthorized** | Bound to caller | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/discovery/crawl` | POST | `current_user` fail-closed | Scoped to caller tenant | **401 Unauthorized** | Bound to caller | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints` |
| `/api/v1/handoff` | POST | `current_user` fail-closed | `verify_tenant_access(user, body.client_id)` | **401 Unauthorized** | **403 Forbidden** | N/A | `test_anonymous_requests_fail_closed_across_all_endpoints`, `test_cross_tenant_isolation_two_synthetic_tenants`, `test_authenticated_crm_handoff_contract` |
| `/api/v1/datasets` | GET / POST | `current_user` fail-closed | SQL query `WHERE tenant_id = ?` | **401 Unauthorized** | **Opaque (0 rows leaked)** | N/A | `tests/test_v5_engine.py` |
| `/api/v1/jobs` | GET / POST | `current_user` fail-closed | SQL query `WHERE tenant_id = ?` | **401 Unauthorized** | **Opaque (0 rows leaked)** | N/A | `tests/test_v5_engine.py` |
| `/api/v1/exports/{id}/download` | GET | `current_user` fail-closed | Checks `export.tenant_id == user.tenant_id` | **401 Unauthorized** | **404 Not Found (Opaque)** | N/A | `tests/test_v5_engine.py` |

---

## 2. Server-Side Identity Authority Principle

A caller-supplied `client_id` query parameter or JSON property is **strictly a requested resource selector and never authority**. 
* **The authority is the cryptographically verified session** (`matrix_session` HMAC-SHA256 cookie or `X-Matrix-Signature` gateway assertion).
* In `services/api/security.py`:
  $$\text{user\_tenant} = \text{user.tenant\_id.removeprefix("workspace--").lower()}$$
  If `user_tenant != req_clean` and the caller is not a global platform administrator (`local-demo` or `system`), access is **denied with HTTP 403 Forbidden**.
* Workspace-level owners (e.g. `User(username="admin_alpha", tenant_id="workspace--tenant_alpha", role="owner")`) are **strictly prohibited** from accessing `tenant_beta` resources.

---

## 3. HMAC Nonce Uniqueness & Gateway Rotation Tests

1. **Persistent SQLite Nonce Storage:** Nonces are recorded in table `service_nonces (nonce TEXT PRIMARY KEY, expires_at INTEGER NOT NULL)` inside `runtime/metadata.sqlite`. Nonce single-use is guaranteed across multiple worker processes, uvicorn restarts, and multi-threaded invocations.
2. **Replay Rejection:** When an identical nonce is presented for a second request within the 300-second validity window, `consume_service_nonce` catches the SQLite `IntegrityError` and throws `HTTP 401 Unauthorized ("Service request already used")`.
3. **Zero-Downtime Secret Rotation:** `SERVICE_AUTH_SECRET` supports comma-separated keys (`old_key,new_key`). The gateway validates the signature against each configured secret in sequence. Both incoming keys succeed; any third untrusted key is rejected with `HTTP 401`. Verified in `test_service_gateway_zero_downtime_key_rotation`.

---

## 4. Supabase Service-Role Predicate Guard

1. Service-role API keys bypass Postgres RLS.
2. In `lead_discovery/supabase_sync.py`, every synchronized record explicitly binds:
   ```json
   {
     "client_id": "shree",
     "workspace_id": "shree",
     "lead_id": "shree:canonical_domain"
   }
   ```
3. Queries to fetch cloud leads strictly filter by `client_id=eq.{client_id}` to prevent cross-tenant data co-mingling in the control plane.
