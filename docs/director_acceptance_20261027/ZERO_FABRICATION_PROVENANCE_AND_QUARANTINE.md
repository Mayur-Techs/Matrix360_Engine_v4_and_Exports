# Zero Fabrication, Provenance, and Quarantine Report

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Audit Standard:** Strict Zero-Fabrication & Evidence Provenance  
**Date:** 27 October 2026  

---

## 1. Runtime Generators Purged

Every reachable code path has been audited and purged of fabricated fallbacks:

1. **`lead_discovery/maps_adapter.py` (DATA-01):**
   - Removed: `.local` domains (`maps.{company}.local`). Unobserved domains remain empty.
   - Removed: Default `"Local Business"`. Stored as `"Unidentified Business Location"`.
   - Removed: Default `"West Bengal"`. Unobserved locations remain `"Unspecified District"`.
   - Removed: Fabricated Google Maps search URLs (`https://www.google.com/maps/search/...`) disguised as verified sources.
   - Removed: Unconditional `PREPASS`, `0.88`, and `QUALIFIED_GENUINE`. Unanchored records marked `NEEDS_REVIEW` or `SOURCE_UNVERIFIED`.
   - Result: Romit export adapter retains 100% contract compatibility while maintaining total factual integrity.

2. **`lead_discovery/supabase_sync.py` (DATA-02):**
   - Removed: Default `client_id = "lakhotia"`.
   - Removed: Default `confidence_score = 0.85`.
   - Removed: Default `qualification_status = "PREPASS"`.
   - Removed: Default `source = "live_evidence_crawler"`.
   - Result: Unassigned leads are rejected from cloud sync to prevent tenant cross-contamination.

3. **`services/api/campaign_routes.py` (DATA-03):**
   - Removed: Default `0.85` confidence and automatic domain substitution for verified URLs.
   - Outreach: WhatsApp and Email briefing templates labeled `marketing_consent_verified=False` and `outreach_channel_eligibility="UNCONFIRMED_SUBJECT_TO_CONSENT"`.

---

## 2. Provenance Invariants

Every production lead record satisfies the following invariants:
1. `record_id` / `lead_id`: Deterministic composite identifier (`{client_id}:{domain}:{contact_slug}`).
2. `workspace_id`: Verified tenant binding.
3. `source`: Provenance tracking (`live_evidence_crawler`, `maps_scraper_v4`, `verified_research`).
4. `retrieval_timestamp`: ISO 8601 UTC timestamp of actual observation.
5. `verified_source_url`: Real observed HTTP URL or Google Maps place ID anchor.
6. `qualification_status`: Evidence-based classification (`PREPASS`, `REVIEW`, `EXCLUDE`).

---

## 3. Non-Destructive Quarantine Protocol

In accordance with Section 3 of the Directive:
- **No Production Leads Purged:** Historical records in `production_vault.db` and preserved milestone jobs (e.g., 5-lead and 20-lead Director acceptance runs) have been maintained intact.
- **Quarantine Classification:** Suspect or unverified records are flagged with `status: NEEDS_REVIEW` or quarantined into `quarantined_legacy/` rather than deleted.
- **Dry-Run Audit:** Active UI and API list endpoints default to verified records, preventing unverified or demo seeds from contaminating production exports.
