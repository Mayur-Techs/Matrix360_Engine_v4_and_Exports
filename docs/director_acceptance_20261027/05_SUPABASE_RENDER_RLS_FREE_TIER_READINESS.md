# 05 — Supabase and Render RLS Free-Tier Readiness Review

**Date:** 27 October 2026  
**Security Reviewer:** Mayur (`Mayur-Techs`)  
**Components:** `supabase/migrations/20261027_harden_tenant_isolation.sql`, `services/api/security.py`, `lead_discovery/supabase_sync.py`

---

## 1. Supabase Tenant Isolation & RLS Migration

### Prior Vulnerability in `20261023_init_matrix360_vault.sql`:
- Tables lacked `workspace_id`.
- Legacy policies granted `FOR ALL TO anon, authenticated USING (true) WITH CHECK (true)`, permitting unauthenticated cross-tenant data exfiltration.

### Reviewed Additive Migration `20261027_harden_tenant_isolation.sql`:
- **Additive Columns:** Adds `client_id TEXT NOT NULL DEFAULT 'unassigned'` and `workspace_id TEXT`.
- **Revoked Anonymous Access:** `REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;`
- **Tenant-Scoped Policies:**
  ```sql
  CREATE POLICY "tenant_isolation_matrix360_leads_select"
    ON public.matrix360_leads
    FOR SELECT
    TO authenticated
    USING (
      client_id = coalesce(current_setting('request.jwt.claims', true)::json->>'tenant_id', '')
      OR workspace_id = coalesce(current_setting('request.jwt.claims', true)::json->>'tenant_id', '')
    );
  ```
- **Readiness Classification:** Migration SQL is staged in source and syntax-checked. **Not applied to production Supabase** pending separate Director authorization.

---

## 2. API Server & Render Free-Tier Hardening

- **Authentication Lifetime:** `services/api/security.py` enforces `SESSION_MAX_AGE_SECONDS = 86400` (24h) session expiration.
- **Fixture Auth Disabled in Production:** Automatically raises `RuntimeError` if `MATRIX_TEST_AUTH_MODE=fixture` is detected on Render or when `ENVIRONMENT=production`.
- **Platform Superadmin Guard:** `verify_platform_admin()` restricts `/api/config-keys` to `role="superadmin"` and rejects standard tenant users.
- **Dual-Sync Scoping:** `lead_discovery/supabase_sync.py` enforces mandatory `workspace_id` filtering in `fetch_leads()`, preventing unpartitioned global table scans.
