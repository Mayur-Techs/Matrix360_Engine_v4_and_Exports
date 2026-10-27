-- Matrix 360 Consulting & LeadScope AI Studio — Additive Security Migration
-- Migration: 20261027_harden_tenant_isolation.sql
-- Workstream Owner: Mayur-Techs
-- Addresses P0 Defect SEC-01: Multi-tenant workspace isolation and strict RLS policies.
-- Status: REVIEWED ADDITIVE MIGRATION (Safe for staging/production review; does not alter existing data destructively).

-- 1. Ensure tenant/workspace identity columns exist on public.leads
ALTER TABLE public.leads 
    ADD COLUMN IF NOT EXISTS client_id TEXT,
    ADD COLUMN IF NOT EXISTS workspace_id TEXT;

-- 2. Ensure tenant/workspace identity columns exist on public.campaign_jobs
ALTER TABLE public.campaign_jobs
    ADD COLUMN IF NOT EXISTS client_id TEXT,
    ADD COLUMN IF NOT EXISTS workspace_id TEXT;

-- 3. Composite performance and tenant isolation indexes
CREATE INDEX IF NOT EXISTS idx_leads_workspace_domain 
    ON public.leads (workspace_id, canonical_domain);

CREATE INDEX IF NOT EXISTS idx_leads_workspace_status 
    ON public.leads (workspace_id, qualification_status);

CREATE INDEX IF NOT EXISTS idx_leads_workspace_created 
    ON public.leads (workspace_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_campaign_jobs_workspace 
    ON public.campaign_jobs (workspace_id, status);

-- 4. Drop overly permissive legacy policies that permitted anon/authenticated universal access
DROP POLICY IF EXISTS "Allow service_role full management on leads" ON public.leads;
DROP POLICY IF EXISTS "Allow service_role full management on campaign_jobs" ON public.campaign_jobs;

-- 5. Strict RLS Policies for leads table
-- 5a. Dedicated service_role policy with full administrative capability
CREATE POLICY "service_role_full_management_leads"
    ON public.leads FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 5b. Authenticated workspace-isolated policy: tenants can only read/write their own workspace rows
CREATE POLICY "authenticated_tenant_scoped_leads"
    ON public.leads FOR ALL
    TO authenticated
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

-- 6. Strict RLS Policies for campaign_jobs table
-- 6a. Dedicated service_role policy
CREATE POLICY "service_role_full_management_campaign_jobs"
    ON public.campaign_jobs FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- 6b. Authenticated workspace-isolated policy
CREATE POLICY "authenticated_tenant_scoped_campaign_jobs"
    ON public.campaign_jobs FOR ALL
    TO authenticated
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

-- 7. Explicitly revoke all public/anon table permissions
REVOKE ALL ON public.leads FROM anon;
REVOKE ALL ON public.campaign_jobs FROM anon;

-- Grant explicit privileges to authenticated and service_role
GRANT SELECT, INSERT, UPDATE, DELETE ON public.leads TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.campaign_jobs TO authenticated;
GRANT ALL ON public.leads TO service_role;
GRANT ALL ON public.campaign_jobs TO service_role;
