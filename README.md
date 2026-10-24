# Matrix 360 Consulting — AI Lead Discovery & Audience Intelligence Platform

An enterprise-grade, evidence-bound B2B lead discovery, autonomous live web crawling, and audience intelligence system.

---

## 🌟 Key Capabilities & System Highlights

1. **Strict Zero Fabrication Policy**:
   - Zero synthetic lead catalogs in production.
   - Zero generated or inferred phone numbers, emails, directors, turnovers, or luxury fleets.
   - If a piece of data is not published on a verified website, it strictly remains `None` / empty.
2. **Dynamic Prompt-to-Query Source Adaptation**:
   - Parses the user prompt dynamically (geography, industry, target role).
   - Generates precision search dorks without hardcoded locations or sectors.
   - Live multi-engine domain harvesting via DuckDuckGo HTML and Lite endpoints.
3. **Deep Web Crawling & Multi-Tier Parsing**:
   - Multi-page in-domain traversal (homepage, `/contact`, `/about`, `/management`, `/plants`, `/facilities`).
   - Cloudflare `data-cfemail` XOR decoding & JS concatenation de-manglers.
   - Schema.org JSON-LD (`Corporation`, `Organization`, `PostalAddress`) extraction.
   - Strict regex validation for emails, phones, West Bengal GSTIN (`19...`), CIN, and Udyam IDs.
4. **Safety, Politeness & Security**:
   - **DNS-Aware SSRF Protection**: Resolves all hostnames via `socket.getaddrinfo` and rejects private, loopback, link-local, and cloud metadata IPs (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`).
   - **Robots.txt Respect**: Polite per-domain robots.txt checks.
   - **Rate Limiting**: Automatic politeness delay between requests to the same domain.
5. **Shortfall & Provenance Guarantees**:
   - If fewer genuine leads exist than requested, the campaign completes with status `partial` (never faking leads to hit targets).
   - Real-time audit metrics: `attempted`, `fetched`, `blocked`, `extracted`, `qualified`, `persisted`.
   - Per-field provenance attached to every record: `verified_source_url`, `crawled_urls`, `retrieval_timestamp`, `page_hash` (SHA256), `extraction_methods`, and `raw_evidence`.
6. **Engine V5 Architecture**:
   - Upgraded V5 engine (`matrix-engine-v5-agentic-dual-drive`, v5.0.0) with 3-layer semantic alias resolution for 25+ bilingual/vernacular headers (*Bhoomi Zila*, *Vyapar*, *Vahan*, *Karta*, *Sampark Mobile*).
   - Universal company qualification, affluence scoring, dual Google Drive cloud bridges, and Avinash CRM integration.

---

## 📅 Summary of Today's Work & Evolution (October 23, 2026)

### Phase 1: Matrix 360 Engine V5 Upgrade (12:39 PM – 01:15 PM)
- **Engine V5 Core**: Upgraded core system to `matrix-engine-v5-agentic-dual-drive` (version 5.0.0).
- **Semantic Alias Resolver**: Added 3-layer semantic alias resolver handling 25+ vernacular Hindi/English headers.
- **Universal Qualification & Scoring**: Built dynamic company qualification and affluence scoring.
- **Integrations**: Implemented dual Google Drive cloud storage bridges and Avinash CRM integration.
- **Backward Compatibility**: Preserved 100% compatibility with V4 deterministic rules and test suites.
- *Commit*: `014a2d9`

### Phase 2: Zero-API Lead Discovery & Web Crawler Studio Integration (01:48 PM – 02:35 PM)
- **Step 0 Integration**: Added Lead Discovery & Web Crawler Studio into the main app shell as "Step 0".
- **Engine Bridge**: Connected discovered web leads directly into the V4/V5 engine for verification and qualification.
- **Cloud & Local Storage**: Created `lead_discovery/supabase_sync.py` for Supabase sync and `engine_v5/unified_pipeline.py` with an embedded SQLite WAL production vault (`runtime/production_vault.db`).
- **Single-Command Launcher**: Built `run_local.py` to start both the FastAPI server and worker with a single command.
- *Commits*: `5c88b4d`, `da4bc0c`

### Phase 3: UI Simplification, Smart Filters & 50-Persona Red Team Stress Test (02:46 PM – 03:15 PM)
- **UI Redesign**: Replaced single-domain crawler input with an effortless 1-click UI for non-technical users.
- **Interactive Smart Filter Pills**: Added interactive pills for Sectors (Foundry, Forging, Steel, 3PL Warehousing, etc.), Turnovers, Roles, and Affluence.
- **Best Leads Ranking**: Implemented composite ranking algorithm sorting by buying power, confidence, and fit.
- **50-Persona Chaos Test**: Built and ran `tests/test_50_red_team_personas.py` to stress-test unicode, corrupted rows, and adversarial prompts, patching all discovered edge-case bugs.
- *Commit*: `f4d7df0`

### Phase 4: Matrix 360 Consulting Branding & Outreach Exports (03:20 PM – 03:45 PM)
- **Official Branding**: Rebranded application with Matrix 360 Consulting logo assets, wordmark, and color scheme.
- **Campaign Scraper Engine**: Built autonomous campaign engine in `services/api/campaign_routes.py` with `/start`, `/status`, and `/export` endpoints.
- **Target Count Selector**: Added target volume selection (`50`, `100`, `200`, `500`, `1000`, `2000` leads).
- **Deduplication Engine**: Built deduplication index against all historical leads in the local vault.
- **Outreach Export Workflows**: Added 1-click WhatsApp campaign CSV export (personalized pitch copy) and Email campaign CSV export.
- *Commits*: `b1e9f00`, `b07e140`

### Phase 5: Live Desktop CRM & Terminal Monitor (03:50 PM – 04:15 PM)
- **Live Desktop CRM Terminal**: Added real-time crawler monitor inside the UI showing:
  - Active crawling URL and company ticker.
  - Live speed counter (`leads/min`) and estimated time to completion (`ETA`).
  - Color-coded live event log stream.
  - Counters for *Pages Crawled* and *Contacts Decoded*.
- **Animated Progress Bar**: Added smooth animated progress bar filling up dynamically during crawling.
- *Commit*: `4e65576`

### Phase 6: System Audit Remediation, Zero Fabrication & Multi-Platform Deployment (05:40 PM – 07:00 PM)
- **Removed All Fabrication**: Completely deleted synthetic lead generator (`generate_fresh_leads`) and quarantined `corporate_promoter_catalog.py`. Cleaned 210 unverified promoter rows from `runtime/production_vault.db`.
- **Quarantined `v5.html`**: Moved `v5.html` into `quarantined_legacy/` with an explanatory notice because it manufactured synthetic turnover and vehicle assets.
- **Dynamic Prompt-to-Query Search Adapter**: Built `lead_discovery/prompt_search_adapter.py` dynamically generating queries for any location/sector across DuckDuckGo HTML and Lite endpoints.
- **Genuine Evidence Crawler**: Built `lead_discovery/live_evidence_crawler.py` with multi-page crawling, Cloudflare XOR decoding, Schema.org JSON-LD parsing, SHA256 page hashes, and strict zero fabrication (missing fields remain `None`).
- **DNS-Aware SSRF Guard & Robots Parser**: Built `lead_discovery/security_guard.py` resolving hostnames to block private/loopback/cloud metadata IPs, safe redirect validation, robots.txt respect, and per-domain rate limiting.
- **Shortfall `PARTIAL` Status**: Updated campaign lifecycle and UI to return `partial` status on shortfall with real audit counts (`attempted`, `fetched`, `blocked`, `extracted`, `qualified`, `persisted`).
- **End-to-End Live Crawling Test**: Created `tests/test_live_crawler_e2e.py` verifying real HTTP network fetches, robots `/private` disallow, Cloudflare XOR decoding, and SQLite vault persistence. All **77 automated tests pass (100% green)**.
- **Multi-Platform Deployment**:
  - **GitHub**: Automated CI pipeline `.github/workflows/ci.yml`.
  - **Vercel**: Static frontend hosting and API rewrites in `vercel.json`.
  - **Supabase**: SQL migration `supabase/migrations/20261023_init_matrix360_vault.sql` with RLS and updated `lead_discovery/supabase_sync.py`.
  - **Render (Free Tier)**: Configured `render.yaml` (512MB RAM, Python 3.12, zero paid persistent disk requirement via Supabase cloud sync) and dynamic `$PORT` binding in `Dockerfile`.
- *Commit*: `2da8bd9`

---

## 🚀 Multi-Platform Deployment Guide

### 1. GitHub Deployment & CI/CD
- **Repository Setup**: Push this repository to your GitHub account on branch `work/mayur` or `main`.
- **Automated CI/CD**: `.github/workflows/ci.yml` runs the complete test suite on Python 3.12 across every push and pull request.
- **Secrets Management**: Configure the following GitHub Secrets:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `OPENAI_API_KEY` (optional)

### 2. Vercel Deployment (Frontend & API Proxy)
- **Root Directory**: Project root.
- **Configuration**: Managed via `vercel.json`.
- **How it works**:
  - Serves static assets directly from `apps/web/` (`index.html`, `app.js`, `styles.css`, `assets/`).
  - Rewrites all `/api/*` and `/health` requests to your backend on Render.
- **Deploy**:
  ```bash
  npm i -g vercel
  vercel
  ```

### 3. Supabase Deployment (Cloud PostgreSQL Lead Vault)
- **Database Migrations**: Run `supabase/migrations/20261023_init_matrix360_vault.sql` in your Supabase SQL Editor.
- **Tables Created**:
  - `public.leads`: Stores verified leads with full provenance, page hashes, extraction methods, and raw evidence.
  - `public.campaign_jobs`: Stores campaign execution state and audit metrics (`attempted`, `fetched`, `blocked`, `extracted`, `qualified`, `persisted`).
- **Configuration**:
  - Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to your environment variables.
  - Discovered leads automatically sync to Supabase PostgreSQL, while retaining local SQLite WAL buffers if offline.

### 4. Render Deployment (Free Tier Compatible)
- **Blueprint**: Uses `render.yaml` optimized for the **Render Free Tier** (512 MB RAM, Python 3.12).
- **Zero Paid Disk Dependency**: Cloud persistence is handled directly via Supabase PostgreSQL, eliminating the need for paid persistent disks.
- **Port Binding**: Automatically binds to Render's dynamic `$PORT` via `Dockerfile` and `uvicorn`.
- **Health Checks**: Verified at `/health` and `/healthz`.
- **Steps to Deploy**:
  1. In the Render Dashboard, click **New +** -> **Blueprint**.
  2. Connect your GitHub repository.
  3. Render detects `render.yaml` and provisions the `matrix360-crawler-api` web service on the free plan.
  4. Under Environment Variables, input your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

---

## 💻 Local Development (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## 🧪 Running Automated Tests

```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```

All 77 automated unit, pipeline, security, and end-to-end crawler tests pass with 100% green status.
