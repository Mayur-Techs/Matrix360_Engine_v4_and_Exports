# Security Tenant RLS & Migration Review

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Target Database:** Supabase PostgreSQL & Local SQLite WAL  
**Status:** ADDITIVE MIGRATION REVIEW COMPLETE — PENDING SEPARATE STAGING/PROD AUTHORIZATION  

---

## 1. Migration Analysis & Additive Safety

### Audited Defect (SEC-01)
In `supabase/migrations/20261023_init_matrix360_vault.sql`:
- `public.leads` and `public.campaign_jobs` tables lacked explicit `client_id` and `workspace_id` columns.
- Policies `Allow service_role full management on leads` and `Allow service_role full management on campaign_jobs` permitted `anon`, `authenticated`, and `service_role` to perform `FOR ALL` operations indiscriminately.

### Additive Migration Drafted: `20261027_harden_tenant_isolation.sql`
- **Zero Destructive DDL:** Does not drop tables or delete existing rows.
- **Safe Column Ingestion:**
  ```sql
  ALTER TABLE public.leads 
      ADD COLUMN IF NOT EXISTS client_id TEXT,
      ADD COLUMN IF NOT EXISTS workspace_id TEXT;

  ALTER TABLE public.campaign_jobs
      ADD COLUMN IF NOT EXISTS client_id TEXT,
      ADD COLUMN IF NOT EXISTS workspace_id TEXT;
  ```
- **Strict Role-Based Policies:**
  1. `service_role`: Full administrative management (`USING (true) WITH CHECK (true)`).
  2. `authenticated`: Scoped strictly to caller's verified JWT workspace claims:
     ```sql
     CREATE POLICY "authenticated_tenant_scoped_leads"
         ON public.leads FOR ALL TO authenticated
         USING (
             workspace_id IS NOT NULL 
             AND workspace_id = COALESCE(
                 NULLIF(current_setting('request.jwt.claims', true)::json->>'workspace_id', ''),
                 NULLIF(current_setting('request.jwt.claims', true)::json->>'client_id', '')
             )
         )
         WITH CHECK (
             workspace_id IS NOT NULL 
             AND workspace_id = COALESCE(
                 NULLIF(current_setting('request.jwt.claims', true)::json->>'workspace_id', ''),
                 NULLIF(current_setting('request.jwt.claims', true)::json->>'client_id', '')
             )
         );
     ```
  3. `anon`: All privileges explicitly revoked (`REVOKE ALL ON public.leads FROM anon;`).

---

## 2. Server-Side Tenant Scoping Enforcement (SEC-02, SEC-03)

Even when the server-side backend connects via `service_role` key, tenant scoping is strictly enforced at every query:
1. `SupabaseLeadSync.fetch_leads(workspace_id=...)`: Requires mandatory verified workspace parameter; executes `workspace_id=eq.{workspace_id}` query.
2. `SupabaseLeadSync.sync_leads(...)`: Rejects unassigned rows missing `client_id` or `workspace_id`.
3. `SupabaseLeadSync.sync_campaign_job(...)`: Attaches server-authoritative `client_id` and `workspace_id`.

---

## 3. Deployment Safety Protocol

> **IMPORTANT:** In accordance with the Director's Directive, this migration has NOT been executed against shared cloud Supabase resources without separate authorization. It is committed as a reviewed additive script ready for controlled staging application.
