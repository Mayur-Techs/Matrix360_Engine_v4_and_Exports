-- Matrix 360 Consulting & LeadScope AI Studio — Supabase Production Lead Vault
-- Migration: 20261023_init_matrix360_vault.sql

-- 1. Leads Table (with Full Evidence Provenance)
CREATE TABLE IF NOT EXISTS public.leads (
    lead_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    canonical_domain TEXT NOT NULL,
    company_phone TEXT,
    company_email TEXT,
    named_contact TEXT,
    role TEXT,
    sector TEXT,
    catchment_district TEXT,
    plant_or_warehouse_address TEXT,
    estimated_turnover TEXT DEFAULT 'Not Disclosed on Website',
    observed_assets_or_fleet TEXT DEFAULT 'Not Disclosed on Website',
    qualification_status TEXT NOT NULL DEFAULT 'PREPASS', -- PREPASS, REVIEW, EXCLUDE
    confidence_score NUMERIC(4, 2) DEFAULT 0.85,
    verified_source_url TEXT,
    crawled_urls TEXT,
    page_hash TEXT,
    retrieval_timestamp TIMESTAMPTZ,
    extraction_methods TEXT,
    evidence_json JSONB DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'live_evidence_crawler',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for lightning fast deduplication and filtering
CREATE INDEX IF NOT EXISTS idx_leads_domain ON public.leads (canonical_domain);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads (qualification_status);
CREATE INDEX IF NOT EXISTS idx_leads_district ON public.leads (catchment_district);
CREATE INDEX IF NOT EXISTS idx_leads_source ON public.leads (source);

-- 2. Campaign Jobs & Audit Trail Table
CREATE TABLE IF NOT EXISTS public.campaign_jobs (
    job_id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    target_count INTEGER NOT NULL,
    leads_found INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'running', -- running, done, partial, error
    audit_metrics JSONB DEFAULT '{}'::jsonb, -- attempted, fetched, blocked, extracted, qualified, persisted
    started_at NUMERIC,
    finished_at NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaign_status ON public.campaign_jobs (status);

-- 3. Row-Level Security (RLS) Policies
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campaign_jobs ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access, anon read/insert if enabled
CREATE POLICY "Allow service_role full management on leads"
    ON public.leads FOR ALL
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated' OR auth.role() = 'anon');

CREATE POLICY "Allow service_role full management on campaign_jobs"
    ON public.campaign_jobs FOR ALL
    USING (auth.role() = 'service_role' OR auth.role() = 'authenticated' OR auth.role() = 'anon');
