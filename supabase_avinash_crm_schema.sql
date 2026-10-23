-- Optional Supabase Migration for Avinash's Unified CRM (branch: work/mayur)
-- Note: The system runs 100% autonomously on its built-in SQLite WAL store
-- (`production_leads_vault.sqlite`) with zero external DB required. Run this
-- SQL in Supabase only if you also want cloud replication into Avinash's CRM DB.

CREATE TABLE IF NOT EXISTS public.matrix360_discovered_qualified_leads (
    lead_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default_workspace',
    client_id TEXT NOT NULL DEFAULT 'lakhotia',
    canonical_domain TEXT NOT NULL,
    crawler_status TEXT NOT NULL,
    v4_v5_class TEXT NOT NULL,
    composite_score INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    sector TEXT NOT NULL,
    named_contact TEXT,
    role TEXT,
    company_phone TEXT,
    company_email TEXT,
    contact_person_phone TEXT,
    contact_person_email TEXT,
    catchment_district TEXT,
    location_type TEXT,
    plant_or_warehouse_address TEXT,
    head_office_address TEXT,
    facility_evidence TEXT,
    msme_or_cert_evidence TEXT,
    estimated_turnover TEXT,
    observed_assets_or_fleet TEXT,
    verified_source_url TEXT,
    crm_stage TEXT NOT NULL DEFAULT 'DISCOVERED_AND_QUALIFIED',
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.matrix360_discovered_qualified_leads ENABLE ROW LEVEL SECURITY;
