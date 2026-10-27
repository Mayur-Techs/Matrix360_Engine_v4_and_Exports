# 02 — Zero Fabrication Full-Stack Audit & Quarantine Ledger

**Date:** 27 October 2026  
**Auditor:** Mayur (`Mayur-Techs`)  
**Standard:** Director Zero Fabrication Directive (P0: Customer Trust)

---

## 1. Full-Stack Audit Findings & Remediations

| Component | Audited Path | Fabricated / Risky Behavior Found | Targeted Remediation | Verification Status |
|---|---|---|---|---|
| **Frontend UI (People Table)** | `apps/web/app.js:1790–1801` | Fallback names rendered `'Director / Promoter'`, `'Managing Director'`, `'Enterprise'`, `'West Bengal'`, and default tier `'A'`. | Replaced with `'Unknown / Not Observed'`, `'Unidentified Organization'`, `'Unspecified District'`, and `'Needs Review'`. | `VERIFIED_LOCAL` |
| **Frontend UI (Source Evidence)** | `apps/web/app.js:1800` | Fabricated `https://${domain}` URL anchor and displayed as "Source Evidence" when no source URL was recorded. | Suppressed anchor; only rendered when `l.verified_source_url` exists. | `VERIFIED_LOCAL` |
| **Frontend UI (Tier Promotion)** | `apps/web/app.js:1712, 1745` | Automatically promoted records to Tier A if `confidence_score >= 0.85` without qualification evidence. | Removed numeric threshold bypass; tier derives strictly from evidence-approved qualification record. | `VERIFIED_LOCAL` |
| **Frontend UI (Org Table)** | `apps/web/app.js:1836–1837` | Defaulted sector to `'Industrial Manufacturing'` and turnover to `'₹25 Cr – ₹100 Cr'`. | Replaced with `'Unspecified Sector'` and `'Not Disclosed / Unverified'`. | `VERIFIED_LOCAL` |
| **Frontend UI (Modal Detail)** | `apps/web/app.js:2200–2206` | Rendered link with text `'Verified Corporate Registry'` even when no evidence URL existed. | Rendered `'No verified URL anchor observed'` when unobserved. | `VERIFIED_LOCAL` |
| **Backend Maps Adapter** | `lead_discovery/maps_adapter.py:59, 156` | Defaulted `client_id` to `"lakhotia"`. | Replaced default with `"unassigned"`, requiring explicit tenant context. | `VERIFIED_LOCAL` |
| **Backend Maps Adapter** | `lead_discovery/maps_adapter.py:97` | Hardcoded uncalibrated confidence scores `0.70 / 0.50`. | Confidence set to `None` when unanchored, or calibrated `0.50` with explicit `NEEDS_REVIEW` flag. | `VERIFIED_LOCAL` |
| **Unified Pipeline** | `engine_v5/unified_pipeline.py:282` | Computed `lead_id = f"{client_id}:{dom}"`, collapsing multiple people at one organization. | Added contact differentiation `{client_id}:{dom}:{contact_slug}` so distinct decision-makers survive deduplication. | `VERIFIED_LOCAL` |

---

## 2. Zero Synthetic Rows in Production Guarantee

- **Database Preservation:** Historical genuine records in `runtime/production_vault.db` and SQLite WAL stores are preserved.
- **Quarantine Manifest:** No bulk deletes performed. Any suspect record with missing provenance remains flagged as `SOURCE_UNVERIFIED` / `NEEDS_REVIEW`.
- **Zero Production Seeding:** Automated test fixtures run strictly within ephemeral or in-memory contexts and never write synthetic rows to live tables.
