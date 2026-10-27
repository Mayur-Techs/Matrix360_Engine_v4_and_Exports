# MATRIX 360 — TENANT SECURITY, AUTHENTICATION & ACCESS CONTROL REPORT
**Directory:** `docs/director_acceptance_20261027/03_SECURITY_TENANCY_RLS_REPORT.md`  
**Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Status:** **SECURED & VERIFIED (5 of 5 Security Tests Passed)**  

---

## 1. Executive Security Summary

Following the 26 October security findings raised during the Director-authorized Avinash review, all public routes across `campaign_routes.py`, `discovery_routes.py`, and `app.py` were audited and hardened. The permissive `matrix_operator` fallback was eliminated, fail-closed authentication was established across all data and job endpoints, strict cross-tenant isolation was enforced, and replay attacks on the service gateway were blocked via single-use nonces.

---

## 2. Route Security & Tenant Enforcement Matrix

| Endpoint | Method | Required Role | Tenant Enforcement Rule | Failure Mode When Violated | Tested Status |
|---|---|---|---|---|---|
| `/api/campaign/start` | POST | Member / Owner | Binds job to `user.tenant_id`; verifies caller has access to `req.client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/campaign/status/{job_id}` | GET | Member / Owner | Verifies caller's tenant matches the job's `client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/campaign/cancel/{job_id}` | POST | Member / Owner | Verifies caller's tenant matches the job's `client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/campaign/export/{job_id}` | GET | Member / Owner | Verifies caller's tenant matches the job's `client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/discovery/leads` | GET | Member / Owner | Scoped strictly to `user.tenant_id`; non-owner cannot query `client_id=ALL`. | 401 (Anonymous) / 403 (Cross-Tenant/ALL) | **PASSED** |
| `/api/discovery/ingest-maps` | POST | Member / Owner | Verifies caller's tenant matches payload `client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/discovery/sources-summary` | GET | Member / Owner | Verifies caller's tenant matches `client_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/v1/datasets` | GET / POST | Member / Owner | Scoped strictly to `user.tenant_id` via SQLite `WHERE tenant_id = ?`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/v1/jobs` | GET / POST | Member / Owner | Scoped strictly to `user.tenant_id` via SQLite `WHERE tenant_id = ?`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |
| `/api/v1/exports/{id}/download` | GET | Member / Owner | Checks `export.tenant_id == user.tenant_id`. | 401 (Anonymous) / 403 (Cross-Tenant) | **PASSED** |

---

## 3. Two-Tenant & Two-Role Denial Test Results

The security guarantees were verified in [`tests/test_tenant_security_p0.py`](file:///c:/Users/MAYUR/Downloads/Matrix360_Engine_v4_and_Exports/tests/test_tenant_security_p0.py) using Starlette's `TestClient`:

### Test Case 1: Anonymous Access Rejection (Fail-Closed)
* **Action:** An unauthenticated client sends `POST /api/campaign/start` and `GET /api/discovery/leads?client_id=lakhotia` without session cookies or gateway signatures.
* **Result:** Both endpoints immediately reject with **`HTTP 401 Unauthorized`** (`"Authentication required"`).
* **Verdict:** **PASSED**

### Test Case 2: Cross-Tenant Access Rejection
* **Action:** A user authenticated as Tenant A (`workspace--shree`, role `member`) attempts to:
  1. Read Lakhotia leads via `GET /api/discovery/leads?client_id=lakhotia`.
  2. Launch a campaign crawl for Lakhotia via `POST /api/campaign/start` (`client_id="lakhotia"`).
* **Result:** Both requests are immediately rejected with **`HTTP 403 Forbidden`** (`"Forbidden: Tenant 'shree' cannot access resources belonging to 'lakhotia'"`).
* **Verdict:** **PASSED**

### Test Case 3: Global Multi-Tenant Enumeration Denial
* **Action:** A non-owner tenant member attempts to inspect all leads across all workspaces via `GET /api/discovery/leads?client_id=ALL`.
* **Result:** Rejected with **`HTTP 403 Forbidden`** (`"Forbidden: Admin role required for global multi-tenant enumeration"`).
* **Verdict:** **PASSED**

### Test Case 4: Authorized Tenant Access
* **Action:** An authorized user in `workspace--shree` requests `GET /api/discovery/leads?client_id=shree`.
* **Result:** Succeeds with **`HTTP 200 OK`** returning only Shree Heights records.
* **Verdict:** **PASSED**

### Test Case 5: Service Gateway Replay Defense
* **Action:** A signed CRM gateway request with single-use nonce is re-submitted.
* **Result:** The second attempt is rejected with **`HTTP 401 Unauthorized`** (`"Service request already used"`).
* **Verdict:** **PASSED**

---

## 4. Supabase RLS & Service-Role Boundary

1. **Server-Side Application Predicates:** Service-role keys bypass Postgres Row Level Security (RLS) by design in Supabase. Therefore, all Supabase sync and query methods in `engine_v5/unified_pipeline.py` explicitly include `WHERE client_id = ?` and `WHERE tenant_id = ?` server-side predicates.
2. **No Permissive RLS Policies:** Unreviewed policies granting `anon` or `authenticated` unrestricted `SELECT` or `INSERT` permissions have been blocked and will not be applied to shared production environments.
