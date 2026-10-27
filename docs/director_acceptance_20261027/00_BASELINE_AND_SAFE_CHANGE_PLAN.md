# 00 — Baseline and Safe Change Plan

**Date:** 27 October 2026  
**Workstream Owner:** Mayur (`Mayur-Techs`, `nikumbhmayur4@gmail.com`)  
**Scope:** Mayur Lead Generation, Web Research, Audience Intelligence, V4/V5 Qualification, and contextual AI specialists only.  
**Baseline Remote SHA:** `ec16bca0eb54ebce86307875b899770c5a420bca`  
**Target Repository:** `https://github.com/Mayur-Techs/Matrix360_Engine_v4_and_Exports`  
**Target Branch:** `main`  
**Render Service:** `srv-dbe7adcs728c73b8hbn0` (auto-deploy active on `main`)

---

## 1. Environment & Ownership Baseline

- **Repository Owner:** Mayur (`Mayur-Techs`).
- **Separated External Modules:**
  - Avinash CRM & shared shell (preserved; delivery deferred).
  - Romit Maps runtime scraper (independent; adapter normalization verified).
  - Tanmayi Creative Studio (independent; untouched).
  - Pratha Marketing campaigns (independent; untouched).
- **Execution Principles:**
  - Zero destructive changes to historical data.
  - Zero synthetic demonstration data in production or live tables.
  - Strict evidence grading across all claims.
  - Truthful representation of heuristic vs. model AI states.

---

## 2. Identified Blockers & Safe Change Plan

1. **Linux CI Blocker:** GitHub Actions run `40470556342` failed 5 tests due to missing SQLite `audit_events` and `datasets` tables during headless Linux execution.  
   *Safe Change:* Add explicit schema initialization fixture in `tests/conftest.py` calling `store.init()`.
2. **Frontend Fabrication Removal:** `apps/web/app.js` contained default fallbacks (`Director / Promoter`, `Managing Director`, `Enterprise`, `West Bengal`, default tier `A`, and synthetic domain URLs).  
   *Safe Change:* Replace with `Unknown / Not Observed`, `Unidentified Organization`, `Unspecified District`, `Needs Review`, and suppress unverified URL anchors.
3. **Backend Maps Adapter Hardcoding:** `lead_discovery/maps_adapter.py` defaulted `client_id` to `"lakhotia"` and assigned uncalibrated confidence scores.  
   *Safe Change:* Default `client_id` to `"unassigned"`, require caller context, and set confidence to `None` when unverified.
4. **Filter Approval Persistence:** `approveFilterDiff()` in `app.js` only updated entity mode without persisting occupations or geographic criteria.  
   *Safe Change:* Persist search parameters, geographic affinities, and criteria cards to `state.currentProfile` and `localStorage`, and re-filter preview immediately.
5. **Chunked Worker Execution Loop:** `services/worker/runner.py` created `DurableCheckpointLedger` but did not execute partition leasing.  
   *Safe Change:* Implement preflight partition discovery, registration, lease acquisition, and commit loop with durable SQLite checkpoints.

---

## 3. Rollback Plan

- If any regression occurs, the commit can be cleanly reverted using `git revert HEAD`.
- Database schema changes are strictly additive (`20261027_harden_tenant_isolation.sql`).
- All tests run locally through `.venv\Scripts\pytest.exe` before any push.
