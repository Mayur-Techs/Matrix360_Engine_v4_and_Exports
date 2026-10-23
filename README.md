# Matrix 360 / Audience Intelligence & Genuine Web Crawler

Evidence-bound B2B lead discovery, autonomous web crawling, and audience-data processing platform.

## Genuine Evidence-Bound Web Crawler & OSINT Engine

1. **Strict Zero Fabrication Policy**:
   - Zero synthetic lead catalogs in production.
   - Zero generated or inferred phone numbers, emails, directors, or turnover values.
   - If a piece of data is not published on a verified website, it remains `None` / empty.
2. **Prompt-to-Query Source Adaptation**:
   - Parses the user prompt dynamically (geography, industry, target role).
   - Generates precision search dorks without hardcoded locations or sectors.
   - Live multi-engine domain harvesting via DuckDuckGo HTML and Lite endpoints.
3. **Deep Web Crawling & Multi-Tier Parsing**:
   - Multi-page in-domain traversal (homepage, `/contact`, `/about`, `/management`, `/plants`).
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

---

## Deployment Guide

### 1. GitHub Deployment & CI/CD
- **Repository Setup**: Push this codebase to your GitHub repository.
- **Continuous Integration**: `.github/workflows/ci.yml` runs automated test suites on Python 3.12 across all pushes and pull requests.
- **Security**: Never commit `.env` or API keys. Configure GitHub Secrets for:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `OPENAI_API_KEY` (optional)

### 2. Vercel Deployment (Frontend & API Proxy)
- **Root Directory**: Project root.
- **Configuration**: Managed via `vercel.json`.
- **How it works**:
  - Serves static assets from `apps/web/` (`index.html`, `app.js`, `styles.css`, `assets/`).
  - Automatically rewrites `/api/*` and `/health` requests to your backend running on Render.
- **Deploy**:
  ```bash
  npm i -g vercel
  vercel
  ```

### 3. Supabase Deployment (PostgreSQL Lead Vault)
- **Database Migrations**: Run `supabase/migrations/20261023_init_matrix360_vault.sql` in your Supabase SQL Editor.
- **Tables Created**:
  - `public.leads`: Stores verified leads with full provenance, page hashes, and extraction methods.
  - `public.campaign_jobs`: Stores campaign execution state and real audit metrics (`attempted`, `fetched`, `blocked`, `extracted`, `qualified`).
- **Configuration**:
  - Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to your environment variables.
  - The crawler automatically syncs fresh leads to Supabase PostgreSQL, while retaining local SQLite WAL buffers if offline.

### 4. Render Deployment (Free Tier Compatible)
- **Blueprint**: Uses `render.yaml` optimized for Render Free Tier (512 MB RAM, Python 3.12).
- **Zero Paid Disk Dependency**: Cloud persistence is handled directly via Supabase PostgreSQL, eliminating the need for paid persistent disks.
- **Port Binding**: Automatically binds to Render's dynamic `$PORT`.
- **Health Checks**: Verified at `/health` and `/healthz`.
- **Steps to Deploy**:
  1. In the Render Dashboard, click **New +** -> **Blueprint**.
  2. Connect your GitHub repository.
  3. Render detects `render.yaml` and provisions the `matrix360-crawler-api` web service.
  4. Under Environment Variables, input your `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

---

## Local Development (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn services.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Running Tests

```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```
