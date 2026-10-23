# Matrix 360 & LeadScope AI Studio — Production Setup & Avinash CRM Integration Guide

This guide describes how the upgraded **Matrix 360 V5 Engine** and the **LeadScope Zero-API Agentic Web Discovery & Crawler System** operate in production on **Render** with **Supabase**, integrate with the **Avinash CRM**, and run completely self-contained without requiring paid scraping APIs.

---

## 1. System Architecture: Two-Phase Agentic Pipeline

The system is architected as an autonomous two-phase workflow:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 0: AUTONOMOUS 8-VECTOR ZERO-API LEAD DISCOVERY & CRAWLER (LeadScope AI)   │
│ 1. Vector 1: Keyless PIN-Code x Industrial Estate Search (DuckDuckGo Lite)        │
│ 2. Vector 2: WB Industrial Estates & Parks Directory (67+ Verified Domains)      │
│ 3. Vector 3: MCA21 Company Registry & CIN Public Index                           │
│ 4. Vector 4: GeM & WB Tender Portal Public Bidder Data                           │
│ 5. Vector 5: Export-Import & DGFT West Bengal Port Filings                       │
│ 6. Vector 6: OpenStreetMap / Overpass Turbo Geo-polygon Boundaries               │
│ 7. Vector 7: Anti-Scrape De-anonymizer (Decodes [at], [dot], Cloudflare XOR)     │
│ 8. Vector 8: Headless Playwright + Resilient HTTP/DOM Fallback (0 browser deps)  │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                   "Send Discovered Leads to Engine →"
                   (POST /api/discovery/send-to-engine)
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DETERMINISTIC MATRIX 360 V5 QUALIFICATION & EXPORT ENGINE               │
│ 1. Semantic Alias Layer (Hindi, Bengali & regional transliteration matching)     │
│ 2. Deterministic West Bengal Geography Resolution (23 WB Districts + PINs)       │
│ 3. Client Targeting & Qualification Rules:                                       │
│    - Lakhotia Industrial: Turnovers ₹10Cr–₹200Cr, commercial/industrial plots    │
│    - Shree Heights: Executive HNI, BMW/Audi/Mercedes, ₹1.5Cr+ residential homes  │
│    - Vrindavan Greens: Nature/villa residential buyers, SUV/green properties     │
│ 4. Output Generation: Client-partitioned CSVs + Combined XLSX + SHA-256 Manifest │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                    Automatic Lead Synchronization
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PRODUCTION STORAGE & SYNC: SUPABASE & AVINASH CRM                                │
│ - PostgREST Direct Upsert (leads table)                                          │
│ - Offline local buffering if Supabase credentials unconfigured                   │
│ - HMAC-SHA256 authenticated REST gateway for Avinash CRM external triggering     │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Zero-API Guarantee (100% Agentic & Self-Contained)

The Lead Discovery Engine is completely self-contained and **does not require paid APIs** (such as Serper, Google Places API, Apify, or BrightData):

1. **Autonomous Web Scraping**: Utilizes keyless DuckDuckGo Lite, open crt.sh Certificate Transparency logs, and Wayback CDX indexes to find company domains.
2. **Industrial Estate Corpus**: Pre-loaded with 67+ verified West Bengal industrial parks, casting foundries, rolling mills, and logistics hubs.
3. **Resilient HTTP/DOM Fallback**: Does not require browser binaries (Playwright) to be installed in lightweight container environments; automatically falls back to an async/sync HTTP BeautifulSoup parser with rotating User-Agents.
4. **Anti-Scraping Token Recovery**: Automatically reverses obfuscated emails (`name [at] domain [dot] com`, Cloudflare `data-cfemail` hex XOR encoding, and reversed CSS directions).

---

## 3. Supabase Database Schema & Setup

### SQL Migration Script
Run the following SQL migration in your Supabase SQL Editor:

```sql
-- 1. Create leads table
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    canonical_domain TEXT,
    company_phone TEXT,
    company_email TEXT,
    named_contact TEXT,
    role TEXT,
    sector TEXT,
    catchment_district TEXT,
    plant_or_warehouse_address TEXT,
    facility_evidence TEXT,
    qualification_status TEXT DEFAULT 'PREPASS',
    confidence_score NUMERIC(5, 2) DEFAULT 0.85,
    source TEXT DEFAULT 'leadscope_ai_zero_api',
    lakhotia_class TEXT,
    shree_class TEXT,
    vrindavan_class TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Performance indexes
CREATE INDEX IF NOT EXISTS idx_leads_domain ON public.leads(canonical_domain);
CREATE INDEX IF NOT EXISTS idx_leads_district ON public.leads(catchment_district);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(qualification_status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);

-- 3. Row-level security (RLS)
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow service role full access"
ON public.leads
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### Environment Variables for Supabase
Set the following environment variables in your deployment environment or `.env` file:

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-secret-key
```

*Note: If these variables are not provided, the application automatically buffers leads into the local SQLite database without raising errors.*

---

## 4. Render Deployment (Production)

### render.yaml
You can deploy both the Web Service and Background Worker directly on Render using the included specification:

```yaml
services:
  - type: web
    name: matrix360-engine
    env: python
    region: singapore
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn services.api.app:app --host 0.0.0.0 --port $PORT --workers 2
    disk:
      name: matrix360-data
      mountPath: /var/data/matrix360
      sizeGB: 10
    envVars:
      - key: PYTHONUNBUFFERED
        value: "1"
      - key: RUNTIME_ROOT
        value: /var/data/matrix360
      - key: SERVICE_AUTH_SECRET
        generateValue: true
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false

  - type: worker
    name: matrix360-worker
    env: python
    region: singapore
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: python -m services.worker.runner
    disk:
      name: matrix360-data
      mountPath: /var/data/matrix360
    envVars:
      - key: PYTHONUNBUFFERED
        value: "1"
      - key: RUNTIME_ROOT
        value: /var/data/matrix360
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_ROLE_KEY
        sync: false
```

---

## 5. Avinash CRM Gateway API Integration

Avinash CRM can interact directly with Matrix 360 using HMAC-SHA256 authenticated REST requests.

### Request Signing Protocol
Every request from Avinash CRM must include the following headers:
- `X-Matrix-Workspace`: The calling CRM workspace ID (e.g. `avinash_crm_prod`).
- `X-Matrix-Timestamp`: Current UTC epoch seconds (must be within ±300 seconds).
- `X-Matrix-Nonce`: Unique 16-64 character random hex string (replay protection).
- `X-Matrix-Signature`: `HMAC-SHA256(SERVICE_AUTH_SECRET, payload)` where:
  `payload = "v1\n" + METHOD + "\n" + PATH + "\n" + WORKSPACE + "\n" + TIMESTAMP + "\n" + NONCE`

### Available Endpoints for Avinash CRM

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/discovery/health` | Health check & engine operational status |
| `GET` | `/api/discovery/leads` | List discovered company leads with filters |
| `POST` | `/api/discovery/zero-api-scale-plan` | Generate autonomous query clusters for lead targets |
| `POST` | `/api/discovery/crawl` | Trigger single-domain live crawl (phones, emails, directors) |
| `POST` | `/api/discovery/send-to-engine` | Bridge discovered leads into an Engine dataset for qualification |
| `POST` | `/api/v1/jobs` | Queue deterministic V5 qualification job |
| `GET` | `/api/v1/jobs/{job_id}/results` | Fetch classified leads with Lakhotia/Shree/Vrindavan tags |
| `GET` | `/api/v1/jobs/{job_id}/exports` | List download links for partitioned CSVs and combined Excel files |
| `POST` | `/api/v1/v5/schema/resolve` | V5 Semantic Alias Agent mapping of unstandardized headers |
| `POST` | `/api/v1/v5/qualify/lead` | Single-lead ad-hoc vehicle and turnover qualification check |

---

## 6. Verification and Smoke Test

To verify the installation locally or in CI/CD, run the test suites:

```bash
# 1. Run all 75 automated tests
python -m pytest -q

# 2. Run specifically the Lead Discovery and V5 Engine test suites
python -m pytest tests/test_v5_engine.py tests/test_lead_discovery_pipeline.py -v
```

All tests pass with **0 failures**, ensuring production readiness.
