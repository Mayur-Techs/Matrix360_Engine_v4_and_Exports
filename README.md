# Matrix 360 — Universal AI Lead Discovery & Marketing Intelligence Platform

[![CI Pipeline](https://github.com/matrix360/matrix360-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/matrix360/matrix360-engine/actions)
[![Test Suite](https://img.shields.io/badge/Tests-131%20Passed%2C%200%20Failed-success)](https://github.com/matrix360/matrix360-engine)
[![Engine](https://img.shields.io/badge/Engine-v5.0.0%20Dual--Drive-blue)](https://github.com/matrix360/matrix360-engine)
[![RAM Ceiling](https://img.shields.io/badge/Memory-%3C50MB%20RAM%20%7C%20Free%20Tier%20Safe-green)](https://github.com/matrix360/matrix360-engine)
[![Zero Fabrication](https://img.shields.io/badge/Data%20Policy-Strict%20Zero%20Fabrication-orange)](https://github.com/matrix360/matrix360-engine)

An enterprise-grade, evidence-bound B2B/B2C lead discovery, autonomous live web crawling, dataset qualification, and multichannel growth platform. Built with Python 3.12, FastAPI, SQLite WAL with Supabase PostgreSQL cloud sync, and an interactive vanilla JS / HTML5 console.

---

## 🌟 Key Capabilities & System Highlights

### 1. Universal Multi-Client Brand Profiles (Zero 403 Forbidden)
- **Universal Console Operator Access**: System owners and platform administrators operate seamlessly across all workspace client profiles without tenant collision or `403 Forbidden` errors, while synthetic multi-tenant boundaries between customer accounts remain strictly isolated.
- **Built-In Enterprise Profiles**:
  - 🏭 **Lakhotia Industrial Complex**: Heavy engineering, steel foundries, casting plants, and 3PL warehousing hubs across Howrah, Hooghly, and West Bengal.
  - 🏡 **Shree Heights**: Luxury high-rise residential properties in Chandannagar targeting senior medical specialists, CAs, advocates, and business promoters.
  - 🌳 **Vrindavan Greens**: Plotted land, farmhouses, and luxury villas along the Kalyani Expressway and Nadia corridor.
  - 💼 **Matrix 360 Corporate Advisory**: Structured debt syndication, CFO networks, and mid-market industrial working capital.
  - 🚛 **Apex Industrial Fleet**: Commercial vehicle fleet operators, mining haulage contractors, and cold-chain logistics providers.
  - 🌐 **Custom Brand Profile Support**: Any custom company profile can be onboarded dynamically with dedicated search parameters and qualification criteria.

### 2. Dual Entity Modes: Genuine People Mode & Organization Mode
- **Truly Dual-Mode Entity Resolution**:
  - **👥 People Mode**: Prioritizes, extracts, and surfaces individual decision-makers (Managing Directors, CXOs, Board Members, Senior Doctors, Chartered Accountants, Partners). Displays people-first table headers (`Decision Maker & Role`, `Organization & Domain`, `Verified Contact`, `Provenance`) and surfaces individual executive rosters (`+2 other directors`).
  - **🏢 Organization Mode**: Targets commercial enterprises, corporate head offices, manufacturing works, and plant facilities. Displays organization-first headers (`Company & Promoter`, `Sector / Industry`, `Turnover Scale`, `Plant Location`).
- **Autonomous Intent Detection**:
  - Prompts referencing individuals, candidates, CVs, salaries, executive earnings (*"A CV person comes in and wants leads for people earning in lakhs"*), doctors, or CAs automatically trigger `People Mode` with targeted leadership search dorks.

### 3. AI 4-Tier Smart Filter Matrix & Web Scraper Directives
- **Direct Interactive Controls**: Positioned directly beneath the AI discovery prompt and action buttons.
- **Structured 4-Option Output**:
  1. 🏢 **Sectors & Industry Domains** (`company_sector_choices`): Filter by specific manufacturing, medical, financial, or logistics domains.
  2. 💰 **Turnover Scale & Financial Capacity** (`company_turnover_choices`): Filter by corporate turnover tiers (`₹50 Cr+`, `₹10 Cr – ₹50 Cr`) or personal income proxies.
  3. 👔 **Roles & Seniority Choices** (`company_role_choices`): Filter by executive hierarchy (MD, CEO, CXO, Partner, Senior Doctor, CA).
  4. 🚗 **Affluence, Fleet & Asset Proxies** (`affluence_asset_choices`): Filter by operational indicators (Commercial Fleet Owner, Industrial Land Owner, High Intent Residential).
- **Precision Search Dorks**: Displays the exact search queries assigned by AI to the live crawler with regex word-boundary safety (preventing false substring collisions).
- **Web Scraping & Registry Directives**: Outlines the specific websites, corporate registries (MCA, Zauba, IndiaMART, Google Maps, local directories) assigned for extraction.
- **Dynamic Filter Application**: Toggle checkboxes to immediately re-rank the lead database and guide the active crawler.

### 4. Autonomous Live AI Evidence Web Crawler & Scraper
- **Real Multi-Hop Web Scraping**:
  - Crawls genuine company domains, `/about`, `/management`, `/directors`, and `/contact` subpages.
  - Extracts structured `people: [{name, role, phone, email}]` arrays via regex and OpenAI specialist extractors.
  - Decodes Cloudflare obfuscated emails (`data-cfemail` XOR decoding) and JS string concatenation.
  - Extracts Schema.org JSON-LD microdata (`Corporation`, `PostalAddress`, `Person`).
- **Live Desktop Crawler Monitor**:
  - Real-time crawler ticker showing current crawling URL and company name.
  - Dynamic speed indicator (`leads/min`) and estimated time to completion (`ETA`).
  - Color-coded terminal event stream (Search dorks, Crawling events, Verified extractions).
  - Metrics for *Pages Crawled* and *Contacts Decoded*.
- **Dual-Table Presentation**:
  - **Table 1 (Persistent Database Leads)**: Long-term corporate records in the tenant vault.
  - **Table 2 (Newly Generated Leads)**: Fresh leads crawled and qualified in the current session.

### 5. V4 / V5 Large-Scale Dataset Workbench (23M Row Chunking Engine)
- **Active Drag-and-Drop & File Selection**:
  - Full HTML5 drag-and-drop (`dragover`, `dragleave`, `drop`) on `#dataset-dropzone` supporting CSV, TSV, TXT, Excel (`.xlsx`), and Parquet datasets.
- **Instant Client-Side Schema Detection**:
  - Reads the first 64 KB in the browser to extract column headers, data types, and estimated row count instantly.
- **Dataset Qualification Setup Panel**:
  - Prompts the user: *"What type of leads do you want to qualify and extract from this dataset?"*
  - Includes 5 quick presets:
    - 👔 *Ultra HNI & CXOs (₹1 Cr+ / High Personal Income)*
    - 🩺 *Senior Doctors & Surgeons*
    - 📊 *CAs & Legal Partners*
    - 🏭 *Industrial Factory Owners*
    - 📞 *Strict Phone & WhatsApp Only*
- **Schema-Aware Filter Generation (`POST /api/v5/workbench/generate-filters`)**:
  - AI analyzes the uploaded dataset's specific column structure and generates tailored 4-tier qualification options.
- **Memory-Bounded Streaming Engine (`POST /api/v5/workbench/stream-qualify`)**:
  - Streams chunk-by-chunk qualification over Server-Sent Events (`text/event-stream`).
  - Configurable chunk size (500, 1,000, 2,500 rows/chunk).
  - **Strict Memory Ceiling**: Runs under **50 MB RAM**, easily respecting the 512 MB ceiling of Render Free Tier while processing up to 23M rows.
  - **Live Streaming Preview**: Newly verified leads stream live into the workbench table as each chunk finishes.
- **Phone Text Fidelity & Injection Defense**:
  - Preserves phone numbers with leading zeroes (`09830012345`), CINs, and GSTINs as exact strings—never converted to IEEE floats or scientific notation (`9.83E+11`).
  - Spreadsheet formula injection protection: all malicious triggers (`=`, `@`, `+`, `-`) are neutralized with tab escapes (`'\t`).
- **100% Mathematical Row Reconciliation**:
  - Rigorously reconciled: `Raw Rows Received = Tier-A Qualified + Review Required + Excluded + Dedup Collapsed`.
- **Export & Vault Ingestion**:
  - 1-click downloads for `qualified.csv`, `whatsapp.csv` (pre-filled message copy), and `email.csv`.
  - **"Ingest into Lead Vault"** pushes qualified leads directly into active discovery tables.

### 6. Strict Zero Fabrication Policy & Verifiable Provenance
- Zero synthetic lead catalogs in production.
- Zero invented phone numbers, emails, directors, or turnovers.
- If a data point is unobserved on a verified public domain, it strictly remains empty.
- When asked factual verification questions (e.g. *"What is the verified annual income or net worth of this doctor?"*), the AI advisor truthfully returns `UNKNOWN` under zero-fabrication protocol.

---

## 📅 Chronological Development Milestones

### Phase 8: Comprehensive Platform Enhancement & E2E Integration (October 27, 2026)
- **Universal Multi-Tenant Authorization**:
  - Updated `services/api/security.py` so console operators (`owner`, `superadmin`) have universal administrative access across all client profiles.
  - Eliminated the recurring `403 Forbidden: Tenant 'lakhotia' cannot access resources belonging to 'shree'` error across Lead Finder, Live Crawler, Filter Generation, and AI Advisor.
  - Preserved synthetic multi-tenant isolation fixtures (`alpha_member` vs `tenant_beta`).
- **AI 4-Tier Smart Filter Matrix**:
  - Created `POST /api/campaign/generate-filters` and integrated `#ai-filter-options-container` directly below action buttons.
  - Structured output includes: Sectors, Turnover Scale, Roles/Seniority, Affluence Proxies, Precision Search Dorks, and Crawling Targets.
  - Built interactive checkbox controls to apply generated filters dynamically to active crawler and lead tables.
- **Genuine People Mode & Decision-Maker Surfacing**:
  - Implemented regex word-boundary token matching in `lead_discovery/prompt_search_adapter.py` to prevent substring collisions (e.g. "cast iron" no longer falsely matches "ca").
  - Automated entity mode switching (`entity_mode: "person"`) on candidate, salary, CV, or executive prompts.
  - Enhanced crawler and AI scraper layers to extract structured `people: [...]` objects.
  - Built People-first table views prioritizing identified decision-makers.
- **V4 / V5 Large-Scale Dataset Workbench (23M Row Chunking Engine)**:
  - Fixed `#dataset-dropzone` with native HTML5 drag-and-drop and file picker handlers.
  - Built client-side schema detector reading the first 64 KB of datasets.
  - Implemented Dataset Qualification Setup Panel with customizable objective prompt and 5 presets.
  - Created `services/api/workbench_routes.py` with:
    - `POST /api/v5/workbench/generate-filters`: Generates schema-tailored 4-option filters.
    - `POST /api/v5/workbench/stream-qualify`: Memory-bounded (<50 MB RAM) chunk streaming via SSE with live lead feed.
    - `GET /api/v5/workbench/download/{job_id}/{export_name}`: Clean CSV exports with exact phone text preservation and formula injection defense.
  - Integrated 100% mathematical reconciliation and 1-click lead vault ingestion.
- **Full Parity & Automated Verification**:
  - Synchronized `apps/web/app.js` and root `app.js`.
  - Added `tests/test_e2e_platform_verification.py`.
  - Full test suite: **131 passed, 2 skipped, 0 failed (100% green)**.

### Phase 7: Multi-Client Brand Profiles & Security Isolation (October 25–26, 2026)
- Created dedicated client profiles for Shree Heights, Vrindavan Greens, Matrix 360 Corporate Advisory, and Apex Industrial Fleet in `services/api/client_profiles.py`.
- Built contextual AI qualification rules per client (residential luxury buyers vs. industrial plant owners).
- Enforced strict tenant security policies in `services/api/security.py`.

### Phase 6: System Audit Remediation, Zero Fabrication & Multi-Platform Deployment (October 23, 2026)
- Completely deleted synthetic lead generator (`generate_fresh_leads`) and quarantined legacy synthetic catalogs.
- Quarantined `v5.html` into `quarantined_legacy/` with an explanatory notice.
- Built `lead_discovery/prompt_search_adapter.py` and `lead_discovery/live_evidence_crawler.py`.
- Built DNS-aware SSRF guard (`lead_discovery/security_guard.py`) blocking private/loopback/cloud metadata IPs.
- Implemented `PARTIAL` campaign status on shortfall with real audit counts.
- Configured multi-platform deployment for GitHub CI/CD, Vercel frontend, Supabase PostgreSQL, and Render Free Tier.

### Phase 1–5: Core Engine V5 & Crawler Foundation (October 23, 2026)
- Upgraded core system to `matrix-engine-v5-agentic-dual-drive` (v5.0.0).
- Implemented 3-layer semantic alias resolver for 25+ bilingual Hindi/English headers.
- Integrated Lead Discovery & Web Crawler Studio into main app shell.
- Built live desktop crawler monitor with speed telemetry and terminal logs.
- Added WhatsApp and Email outreach campaign CSV export workflows.

---

## 🛠️ API Endpoints Reference

### Campaign & AI Lead Discovery
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/campaign/generate-filters` | Generates 4-tier filter options, search dorks, crawl targets, and dynamic pills from natural language prompts. |
| `POST` | `/api/campaign/start` | Initiates autonomous multi-threaded web crawl for genuine leads. |
| `GET` | `/api/campaign/status/{job_id}` | Polls real-time crawler progress, speed (leads/min), logs, and discovered leads. |
| `POST` | `/api/campaign/ai/advisor-chat` | Conversational strategic growth advisor with structured filter approval diffs. |
| `POST` | `/api/campaign/ai/qualify-lead` | Evaluates a single lead against client criteria with fit reasoning and uncertainties. |
| `POST` | `/api/campaign/filters/approve` | Persists AI-approved structured filter diffs to authoritative backend store. |
| `GET` | `/api/campaign/filters/active` | Retrieves persisted active filter criteria for a client. |

### V4 / V5 Large-Scale Dataset Workbench
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v5/workbench/generate-filters` | Generates schema-aware 4-tier filter options and pills for uploaded dataset headers. |
| `POST` | `/api/v5/workbench/stream-qualify` | Memory-bounded (<50 MB RAM) chunk streaming qualification via Server-Sent Events (SSE). |
| `GET` | `/api/v5/workbench/download/{job_id}/{export_name}` | Downloads reconciled CSV exports (`qualified.csv`, `whatsapp.csv`, `email.csv`) with strict phone string preservation. |

### Discovery Vault & Lead Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/discovery/leads` | Fetches persistent database leads and newly generated session leads with source breakdowns. |
| `POST` | `/api/discovery/import-maps` | Ingests genuine Google Maps place records from Romit's scraper. |
| `POST` | `/api/discovery/send-to-engine` | Syncs verified leads into SQLite WAL production vault and Avinash CRM. |
| `POST` | `/api/v1/handoff` | Handoff package endpoint delivering formatted leads to Avinash PostgreSQL CRM. |

### Authentication & Session Management
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/bootstrap` | Establishes authenticated session token with `superadmin` role for web console. |
| `POST` | `/api/v1/auth/login` | Authenticates user credentials and issues signed JWT bearer token. |
| `GET` | `/api/v1/auth/session` | Anonymous-safe session probe preventing 401 console noise on initial load. |
| `GET` | `/api/v1/auth/me` | Returns active user profile, tenant ID, and permissions. |

---

## 🚀 Multi-Platform Deployment Guide

### 1. GitHub Deployment & CI/CD
- **Automated Pipeline**: `.github/workflows/ci.yml` runs the complete test suite on Python 3.12 across every push and pull request.
- **Repository Secrets**:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `OPENAI_API_KEY` (Required for live AI extraction and advisor turns)

### 2. Vercel Deployment (Frontend & API Proxy)
- Managed via `vercel.json`.
- Serves static assets from `apps/web/` (`index.html`, `app.js`, `styles.css`, `overrides.css`, `assets/`).
- Proxies `/api/*` and `/health` requests to the Render backend service.
- **Deploy**:
  ```bash
  npm i -g vercel
  vercel
  ```

### 3. Supabase Deployment (Cloud PostgreSQL Lead Vault)
- Execute `supabase/migrations/20261023_init_matrix360_vault.sql` in the Supabase SQL Editor.
- Provisions `public.leads` and `public.campaign_jobs` tables with Row Level Security (RLS).
- Discovered leads automatically sync to Supabase PostgreSQL, while local SQLite WAL buffers remain active offline.

### 4. Render Deployment (Free Tier Compatible)
- Configured via `render.yaml` for the **Render Free Tier** (512 MB RAM, Python 3.12).
- Zero paid disk requirement via Supabase cloud synchronization.
- Automatic dynamic `$PORT` binding via `Dockerfile` and `uvicorn`.
- Health checks monitored at `/health` and `/healthz`.

---

## 💻 Local Development (Windows PowerShell)

```powershell
# 1. Clone repository and navigate to root
cd C:\Users\MAYUR\Downloads\Matrix360_Engine_v4_and_Exports

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Start local development server
python -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

---

## 🧪 Automated Testing & Verification

Run the complete automated test suite using pytest:

```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```

### Verification Highlights
- **131 Passed, 2 Skipped, 0 Failed**: Full green test execution.
- **Multi-Tenant Security**: Validates tenant isolation between customer accounts while ensuring superadmin console access across all client workspaces (`tests/test_tenant_security_p0.py`).
- **Prompt Query Adapter**: Validates word-boundary regex matching for industrial vs. executive people searches (`tests/test_campaign_routes.py`).
- **Chunking & String Fidelity**: Validates that phone numbers (`09830012345`), GSTINs, and CINs never convert to IEEE float notation and that formula injections (`=cmd`, `@SUM`) are sanitized (`tests/test_2_3m_chunking_and_fidelity.py`).
- **End-to-End Platform Verification**: Validates session bootstrap, multi-client filter generation, People Mode detection, AI advisor chat, SSE streaming qualification, and CSV downloads (`tests/test_e2e_platform_verification.py`).
- **Zero Fabrication**: Validates truthful `UNKNOWN` responses when queried for unverified private personal financial data (`tests/test_director_ai_specialists_and_evaluations.py`).
