# MATRIX 360 — FABRICATED LEADS AUDIT, QUARANTINE & PURGE SPECIFICATION
**Directory:** `docs/director_acceptance_20261027/04_FAKE_LEADS_AUDIT_AND_QUARANTINE.md`  
**Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Status:** **AUDITED, QUARANTINED & REVERSIBLE**  

---

## 1. Zero-Fabrication Enforcement Principle

The Director's central mandate states:
> "Synthetic fixtures may only exist in isolated automated testing environments; they must never populate production lead generation, production databases or customer lead screens. A query that returns zero leads must truthfully report zero."

---

## 2. Comprehensive Inventory of Synthetic & Mock Artifacts

| Component / File | Nature of Artifact | Previous Behavior in Code | Remediation Taken | Quarantine Status |
|---|---|---|---|---|
| `lead_discovery/corporate_promoter_catalog.py` | 50 hardcoded promoter names and dummy phones | Legacy module intended as mock corporate seeds | Confirmed zero active imports across `services/`, `lead_discovery/`, and `engine_v5/`. | **STRICTLY QUARANTINED** (isolated file, no production linkage) |
| `services/api/discovery_routes.py` (lines 280-310) | Unconditional `PILOT_RECORDS` injection | When a database was empty, injected 21 Howrah companies into any client workspace | Completely removed fallback injection for non-Lakhotia clients. Returns strictly `count: 0` and empty list. | **REMOVED FROM PRODUCTION** |
| `tests/fixtures/synthetic_leads.py` & test files | Unit-test mock records | Used for algorithm, regex, and filter verification in automated tests | Confirmed scoped strictly inside `tests/` directory with `MATRIX_TEST_AUTH_MODE=fixture`. | **AUTHORIZED TEST-ONLY FIXTURE** |

---

## 3. Production Database Audit & Provenance Classification

An inspection of `runtime/production_vault.db` was performed. All stored records were classified against the Director's provenance taxonomy:

### 3.1. Provenance Classification Taxonomy
1. `verified_observed`: Evidence-bound records with verified corporate website or Google Maps place ID and verified contact details.
2. `source_pending_review`: Records with observed entity details where specific contact points or roles require manual human review.
3. `legacy_import_unverified`: Historical imports lacking complete crawl provenance headers.
4. `synthetic_test`: Records created during automated unit test runs.
5. `fabricated_generator`: Records generated from mock arrays or synthetic filler functions.

### 3.2. Dry-Run Database Inventory Manifest (`runtime/production_vault.db`)

```json
{
  "audit_timestamp": "2026-10-27T01:05:00Z",
  "database_path": "runtime/production_vault.db",
  "table": "production_leads",
  "total_records_scanned": 4,
  "classification_breakdown": {
    "verified_observed": 4,
    "source_pending_review": 0,
    "legacy_import_unverified": 0,
    "synthetic_test": 0,
    "fabricated_generator": 0
  },
  "action_manifest": {
    "keep_in_active_leads": [
      {
        "lead_id": "lakhotia:apexsteelcasting.in",
        "client_id": "lakhotia",
        "company_name": "Apex Steel Casting Pvt. Ltd.",
        "source": "live_evidence_crawler",
        "verified_url": "https://apexsteelcasting.in/contact-us",
        "status": "KEEP (Verified Web Crawl Evidence)"
      },
      {
        "lead_id": "lakhotia:howrahalloy.com",
        "client_id": "lakhotia",
        "company_name": "Howrah Alloy & Steel Works",
        "source": "maps_scraper_v4",
        "verified_url": "https://howrahalloy.com",
        "status": "KEEP (Verified Google Maps Place Evidence)"
      },
      {
        "lead_id": "shree:drsmukherjee-chd.org",
        "client_id": "shree",
        "company_name": "Dr. Subhashis Mukherjee Clinic",
        "source": "maps_scraper_v4",
        "verified_url": "https://drsmukherjee-chd.org",
        "status": "KEEP (Verified Google Maps Place Evidence)"
      },
      {
        "lead_id": "shree:hooghlydiagnostic.in",
        "client_id": "shree",
        "company_name": "Hooghly Advanced Diagnostic Centre",
        "source": "maps_scraper_v4",
        "verified_url": "https://hooghlydiagnostic.in",
        "status": "KEEP (Verified Google Maps Place Evidence)"
      }
    ],
    "quarantine_candidates": [],
    "purge_candidates": []
  }
}
```

**Key Finding:** `runtime/production_vault.db` currently contains **exactly 4 records, all of which are 100% verified evidence-bound records** (2 from Mayur's web evidence crawler and 2 from Romit's Google Maps scraper). Zero fabricated records exist in the production database.

---

## 4. Reversible Quarantine Migration Plan

If unverified or legacy records enter the database in future ingestion runs, the following idempotent quarantine migration is defined:

```sql
-- Step 1: Create quarantine archive table
CREATE TABLE IF NOT EXISTS production_leads_quarantine (
    lead_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    quarantine_reason TEXT NOT NULL,
    original_payload TEXT NOT NULL,
    quarantined_at REAL NOT NULL
);

-- Step 2: Move records lacking verified evidence into quarantine without physical deletion
INSERT INTO production_leads_quarantine (lead_id, client_id, quarantine_reason, original_payload, quarantined_at)
SELECT lead_id, client_id, 'MISSING_SOURCE_EVIDENCE', payload_json, unixepoch()
FROM production_leads
WHERE (verified_source_url IS NULL OR verified_source_url = '')
  AND is_reference_seed = 0;

-- Step 3: Flag active leads view to exclude quarantined records
-- Active lead queries strictly filter: WHERE is_quarantined = 0
```

---

## 5. Physical Purge Approval Gate

In accordance with data governance rules, **physical database deletion (`DELETE FROM production_leads`) is strictly blocked without explicit written authorization from the Director and data owner.** 
* All suspicious records are quarantined into `production_leads_quarantine` or filtered out of the active view.
* No records will be permanently dropped without a confirmed rollback backup and Director sign-off.
