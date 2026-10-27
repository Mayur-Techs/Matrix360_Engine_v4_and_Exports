# MATRIX 360 — BROWSER ACCEPTANCE & AVINASH CRM HANDOFF EVIDENCE
**Directory:** `docs/director_acceptance_20261027/18_BROWSER_AND_AVINASH_HANDOFF_EVIDENCE.md`  
**Execution Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Collaborators:** Avinash (CRM & Multi-Tenant Boundary Owner), Romit (Maps Scraper V4 Owner)  
**Status:** **SYNTHETIC FLOWS VERIFIED & WORKSTREAM BOUNDARIES RESPECTED**

---

## 1. Offline Browser Acceptance Verification

All user-facing workflows were verified offline using local assets and synthetic API responses:

### 1.1. Dynamic Client Navigation & Entity Modes
* **People Mode (`👥 People Mode`):**
  * Auto-activates when switching to **Shree Heights** or **Vrindavan Greens**.
  * Renders columns: `#`, `Decision Maker & Role`, `Organization & Domain`, `District / Geo`, `Verified Contact`, `Source Origin`, `Tier`, `AI Fit Reasoning & Provenance`, `Action`.
* **Organization Mode (`🏢 Org Mode`):**
  * Auto-activates when switching to **Lakhotia Industrial Complex**, **Matrix 360 Advisory**, or **Apex Fleet**.
  * Renders columns: `#`, `Company & Promoter`, `Domain`, `District / Plant`, `Verified Contact`, `Source Origin`, `Sector / Industry`, `Turnover Scale`, `Tier`, `Action`.

### 1.2. Three Criteria Cards
* `#search-criteria-card`: Populates active discovery prompt, target dorks, and entity scope.
* `#qualification-criteria-card`: Displays client-specific criteria (e.g. Chandannagar residence, doctor/CA designations, minimum turnover).
* `#ai-criteria-card`: Configures evaluation weights, strictness levels, and evidence thresholds.

### 1.3. Dual Distinct Lead Tables
* **Table 1 (`#existing-leads-table`):** Positioned on top. Populated from persistent vault database leads (`N` leads).
* **Table 2 (`#newly-generated-leads-table`):** Positioned directly below. Shows only newly discovered leads associated with active `job_id` (`M` leads).
* **Empty State:** When 0 leads match, displays `#discovery-empty-state` with truthful zero counts and action button `[⚡ Generate Real Leads]`.

### 1.4. Responsive Breakpoints & Viewports
* **390px (Mobile Portrait):** Tables switch to card-based horizontal scrolling; sidebar collapses to drawer hamburger menu.
* **768px (Tablet):** Compact tables; criteria cards stack in 2-column layout.
* **1440px (Desktop):** Full 3-card horizontal grid, dual tables with full column width and evidence drilldown modals.

---

## 2. Romit Google Maps Adapter Boundary

1. **Independent Module Preservation:**
   * Romit's independent crawler (`workstreams/mayur/maps_scraper_v4`) was **not modified, rewritten, or called live**.
   * Zero live Google Maps API or Outscraper network requests were initiated.
2. **Canonical Consumption Contract (`lead_discovery/maps_adapter.py`):**
   * Acts purely as a **receiver and normalizer** for Romit's `matrix360-lead-export.v1` output payloads.
   * Extracts canonical domain, preserves phone text string without scientific notation, prevents duplicate re-ingestion, and marks source badge as `maps_scraper_v4`.

---

## 3. Avinash CRM Signed Gateway & Handoff Pipeline

1. **Server-to-Server Gateway Security:**
   * Browser JS **never** holds service-role credentials or environment secrets.
   * Browser triggers `POST /api/v1/handoff` with session cookie; backend authenticates caller, verifies tenant isolation, and logs audit record.
2. **Handoff Endpoint (`POST /api/v1/handoff`):**
   * Implemented in `services/api/app.py`.
   * Computes SHA256 idempotency hash over approved lead array.
   * Returns signed receipt confirming handoff to Avinash PostgreSQL pipeline without performing unauthorized writes to shared production databases.

### Remaining Integration Tasks for Avinash
1. **Shared Secret Exchange:** Inject agreed `MATRIX_SERVICE_AUTH_SECRET` into Avinash's CRM staging environment.
2. **Webhook Listener:** Wire Avinash's inbound lead queue to ingest the verified handoff payload from `POST /api/v1/handoff`.
3. **Suppression Feedback Loop:** Expose a read-only endpoint in Avinash's CRM allowing Mayur's discovery engine to check existing CRM accounts and suppress already-contacted leads before crawling.
