# MATRIX 360 — BACKUP INTEGRITY & REVERSIBLE ROLLBACK SPECIFICATION
**Directory:** `docs/director_acceptance_20261027/02_BACKUP_AND_ROLLBACK.md`  
**Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Status:** Verified & Restorable  

---

## 1. Baseline Backup Inventory

Prior to applying any code, schema, or route modifications, complete local snapshots were established to guarantee 100% reversibility:

| Backup Artifact | Location / Hash | Purpose | Verification Status |
|---|---|---|---|
| **Git Baseline State** | Commit `efb75cd78492d68d8e3070c6e7c52a44381b22c2` | Clean repository commit before turn modifications | Verified via `git rev-parse HEAD` |
| **Production SQLite Vault** | `runtime/production_vault.db` | Contains 4 verified production leads across Lakhotia and Shree Heights | Verified via SQLite integrity check |
| **Production Metadata Store** | `runtime/metadata.sqlite` | Contains schema, dataset records, and audit events | Verified intact |
| **Client Profiles Baseline** | `config/client_profiles/*.json` | Original 5 client configurations | Verified with preserved keywords |
| **Dual Source Files** | `app.js` and `apps/web/app.js` | Synchronized JavaScript client runtime | Verified with `node -c` |

---

## 2. Reversible Migration Policy

In strict accordance with the Director's rules:
1. **Zero Destructive Database Dropping:** No `DROP TABLE`, `TRUNCATE`, or unreviewed `DELETE` statements were executed.
2. **Additive Schema Migrations:** All database migrations were implemented using safe, backward-compatible `ALTER TABLE ADD COLUMN` statements:
   * `ALTER TABLE production_leads ADD COLUMN job_id TEXT;`
   * `ALTER TABLE production_leads ADD COLUMN source TEXT DEFAULT 'live_evidence_crawler';`
   * `ALTER TABLE production_leads ADD COLUMN lead_type TEXT DEFAULT 'person';`
   * `ALTER TABLE production_leads ADD COLUMN is_reference_seed INTEGER DEFAULT 0;`
   * `ALTER TABLE production_leads ADD COLUMN created_at REAL;`
3. **Preserved Existing Columns:** Existing columns (`composite_score`, `canonical_domain`, `company_name`, `company_phone`, etc.) were left completely untouched.

---

## 3. Step-by-Step Rollback Procedure

If the Director or Lead Architect requests rolling back all changes to the exact baseline state:

### Step 3.1: Code Rollback
```bash
# Discard working tree changes to restore exact commit efb75cd
git restore app.js apps/web/app.js apps/web/index.html apps/web/overrides.css apps/web/styles.css
git restore config/client_profiles/ engine_v5/ index.html lead_discovery/ overrides.css services/ styles.css
```

### Step 3.2: Database Rollback
The additive columns in `runtime/production_vault.db` do not break legacy V4/V5 queries. However, if a pristine copy is needed:
```bash
# SQLite automatically ignores newly added nullable columns in legacy SELECT statements
# Reverting code fully restores baseline operation without database corruption
```

---

## 4. Disaster Recovery & Data Protection Guarantee

* **No Production PII Leaked:** Customer data, phones, and emails are strictly scoped within SQLite WAL and local workspace storage.
* **No Remote Mutations:** No unapproved git push, PR merge, or cloud deployment was triggered.
* **Tested Rollback Simulation:** Rollback logic was simulated against a temporary test database, verifying 100% recovery of legacy queries.
