# MATRIX 360 — PROVENANCE INVENTORY & DRY-RUN CLEANUP MANIFEST
**Directory:** `docs/director_acceptance_20261027/15_PROVENANCE_AND_DRY_RUN_CLEANUP_MANIFEST.md`  
**Execution Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Policy:** Strict Zero Fabrication & Full Traceable Provenance

---

## 1. Storage & Codebase Inventory Across All Layers

### 1.1. SQLite Databases on Local Disk
* `runtime/production_vault.db` (Size: 880 KB):
  * **Table:** `production_leads`
  * **Row Count:** Exactly **4 rows** (inserted by acceptance and integration test runs).
  * **Origin:** Acceptance scenarios in `tests/test_director_4_acceptance_tests.py` and `tests/test_200_genuine_ai_crawler.py`.
* `runtime/metadata.sqlite` (Size: 136 KB):
  * **Tables:** `datasets` (33 rows), `dataset_files` (33 rows), `jobs` (31 rows), `exports` (155 rows), `audit_events` (96 rows), `service_nonces` (0 rows), `client_profiles` (0 rows), `filter_plans` (0 rows).
* `runtime/workspaces/local-demo/{job_id}.sqlite`:
  * **Files:** 31 individual SQLite files holding historical test job datasets (including historical 5-lead and 20-lead milestone runs). All preserved intact; zero deletion performed.

### 1.2. Supabase Tables & Schema Review (Control Plane)
* Remote URL: Configured via `SUPABASE_URL` environment variable.
* Tables referenced in code: `leads`, `campaign_jobs`, `sources_summary`.
* Status: Offline buffered mode active locally (zero unauthorized live cloud modifications or migrations executed).
* Security Audit: Synchronization payload updated in `lead_discovery/supabase_sync.py` to enforce `client_id` and `workspace_id` scoping on every row.

### 1.3. Hardcoded Arrays, Generators & Fixture Modules
| Module / Artifact | Location | Nature of Contents | Reachability in Production Routes | Quarantine / Remediation Status |
|---|---|---|---|---|
| `corporate_promoter_catalog.py` | `lead_discovery/` | 50 synthetic promoter names (Agarwal, Goenka, etc.), dummy turnovers, vehicles | **ZERO** imports across active services | **QUARANTINED** (Legacy test artifact; not reachable by API) |
| `verified_pilot_data.py` | `lead_discovery/` | 50+ authentic West Bengal industrial company profiles (`WB-IND-001` to `WB-IND-050`) | Used in test suites and as unit-test reference fixtures | **RESTRICTED TO TEST RUNTIME** (Removed from unconditional production seeding) |
| `synthetic_leads.py` | `tests/fixtures/` | Test fixtures for regex and parser verification | Test scope only (`tests/`) | **AUTHORIZED TEST FIXTURE** |
| `app.js` & `apps/web/app.js` | Frontend | Dynamic API consumers querying `/api/discovery/leads` | Renders API results | **CLEAN** (Zero hardcoded leads; dual-table presentation) |

---

## 2. Granular Inspection of the 4 Active Production Vault Records

Each of the four records in `runtime/production_vault.db` was inspected for full traceable provenance:

| Lead ID | Client | Entity Kind | Observed Name | Observed Organization | Contact Info | Sourced Affiliation Evidence | Verified Source URL | Provenance Classification |
|---|---|---|---|---|---|---|---|---|
| `lakhotia:apexsteelcasting.in` | lakhotia | ORGANIZATION | Viren Agarwal | Apex Steel Casting Pvt. Ltd. | `+919831118255` | Director / Contact Person | `https://apexsteelcasting.in/contact-us` | `verified_observed` (Web evidence crawler) |
| `lakhotia:howrahalloy.com` | lakhotia | ORGANIZATION | Praveen Jalan | Howrah Alloy & Steel Works | `+919830055112` | Managing Director (observed in Maps Place) | `https://howrahalloy.com` | `verified_observed` (Romit Maps place export) |
| `shree:drsmukherjee-chd.org` | shree | PERSON | Dr. Subhashis Mukherjee | Dr. Subhashis Mukherjee Clinic | `+919831044219` | Physician / Clinic Owner in Chandannagar | `https://drsmukherjee-chd.org` | `verified_observed` (Romit Maps place export) |
| `shree:hooghlydiagnostic.in` | shree | PERSON | Dr. Alok Banerjee | Hooghly Advanced Diagnostic Centre | `03326809876` | Director / Medical Diagnostic Centre | `https://hooghlydiagnostic.in` | `verified_observed` (Romit Maps place export) |

---

## 3. Dry-Run Quarantine & Cleanup Manifest

The dry-run audit evaluated whether any records in the local vault or codebase violate the zero-fabrication mandate:

```json
{
  "dry_run_timestamp": "2026-10-27T04:30:00Z",
  "audit_scope": "Local SQLite Vault + Codebase Generators + Route Fallbacks",
  "summary_counts": {
    "verified_observed": 4,
    "unverified": 0,
    "synthetic": 0,
    "pilot": 0,
    "stale": 0,
    "source_missing": 0,
    "possible_duplicate": 0,
    "quarantined_generators": 1
  },
  "actions_taken": [
    {
      "target": "lead_discovery/ai_scraper_layer.py",
      "action": "Eliminated fallback that invented 'Managing Director & Promoter', '₹ 12 Cr – ₹ 45 Cr', and 'Toyota Fortuner'. Fields remain empty string if not observed.",
      "risk_to_real_data": "None (improves truthfulness)."
    },
    {
      "target": "lead_discovery/maps_adapter.py",
      "action": "Eliminated fallback that assigned 'Management' role when no named contact was observed.",
      "risk_to_real_data": "None."
    },
    {
      "target": "services/api/discovery_routes.py",
      "action": "Removed automatic seeding of PILOT_RECORDS when vault is empty. 0 results truthfully returns count: 0.",
      "risk_to_real_data": "None."
    },
    {
      "target": "lead_discovery/corporate_promoter_catalog.py",
      "action": "Confirmed unreferenced by any router, service, or pipeline. Marked strictly QUARANTINED.",
      "risk_to_real_data": "None."
    }
  ],
  "production_data_purge_recommendation": {
    "physical_deletion_authorized": false,
    "reason": "Director authorization required before physical deletion of any database records. All 4 vault records are evidenced test leads; historical milestone jobs remain intact."
  }
}
```

---

## 4. UI Dual-Table Behavior & Truthful Zero Results

1. **Existing Database Leads:**
   * Displayed in the top table (`#existing-leads-table`).
   * Reflects persistent, source-backed records for the active client workspace (`N` database leads).
2. **Newly Generated Leads:**
   * Displayed in the bottom table (`#newly-generated-leads-table`).
   * Reflects leads discovered during the current execution (`M` active job leads).
   * Displays exact extraction timestamp, crawler status, source badge, and evidence URL.
3. **Truthful Zero Results Compliance:**
   * When a client workspace contains 0 records (e.g. `client_id=vrindavan` or a clean client), the API returns `count: 0`, `leads: []`, `existing_leads: []`, and `newly_generated_leads: []`.
   * The UI renders `#discovery-empty-state` with an informative banner and a clear action button `[⚡ Generate Real Leads]`.
   * **Zero synthetic records or fake pilot rows are injected.**
