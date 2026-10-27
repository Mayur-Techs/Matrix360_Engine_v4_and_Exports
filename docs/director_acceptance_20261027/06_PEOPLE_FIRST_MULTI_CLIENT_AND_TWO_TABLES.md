# 06 — People-First Multi-Client & Two-Table Separation

**Date:** 27 October 2026  
**Engineer:** Mayur (`Mayur-Techs`)  
**Components:** `apps/web/app.js`, `services/api/discovery_routes.py`, `engine_v5/unified_pipeline.py`

---

## 1. People-First Entity Architecture

- **Domain Deduplication Bug Fixed:** Previously, lead records were indexed solely by domain (`{client_id}:{dom}`), which collapsed multiple distinct executives at the same enterprise.
- **Contact Differentiation:** Updated `lead_id` formulation to `{client_id}:{canonical_domain}:{contact_slug}`.
- **Multi-Person Proof:** Regression test `test_tenant_06_multi_person_at_same_domain_retained` proves that two decision-makers at the same organization (e.g. Dr. Subhashis Mukherjee and a clinic administrator at `bcroyclinic-chd.in`) retain separate records, roles, contact channels, and qualification rationales.

---

## 2. Multi-Client Scalability (Beyond Pilot Five)

- The engine dynamically supports arbitrary onboarded clients via `services/api/campaign_routes.py`.
- Adding a new client (e.g. client 6) requires no hardcoded code edits.
- Client context is passed via authenticated session `tenant_id` or explicit `client_id` payload.
- Fallback to `"lakhotia"` has been eradicated across all API routes and adapters; unconfigured clients receive truthful 404/400 errors or `'unassigned'` status.

---

## 3. Two-Table Separation in Frontend (`app.js`)

1. **Table 1: Existing Database Leads (Top Table)**
   - Renders persistent enterprise records retrieved from the tenant-scoped database vault.
   - Shows total count, Tier A count, and phone numbers count.
   - When no records match, displays: *"No existing database records match the selected filters."*
2. **Table 2: Newly Generated Leads (Bottom Table)**
   - Renders fresh leads discovered during the current job session.
   - Tagged with the active `current_job_id`.
   - When no crawl has occurred, displays: *"No newly generated leads in this session yet."*
- **Zero Fabrication:** Neither table populates fake sample leads, fictitious promoter names, or simulated green badges.
