# 03 — AI Specialists Live Context & Filter Approval Verification

**Date:** 27 October 2026  
**Architect:** Mayur (`Mayur-Techs`)  
**Components:** `services/api/ai_platform.py`, `apps/web/app.js`, `tests/test_director_ai_specialists_and_evaluations.py`

---

## 1. Specialist Orchestrator Architecture

Four Mayur-owned specialists are implemented in `services/api/ai_platform.py`:
1. **Audience Strategy Specialist:** High-level objective interpretation, persona mapping, and client business goal alignment.
2. **Discovery Specialist:** Maps search queries, crawl targets, geography boundaries, and live web discovery.
3. **Data Cleaning Specialist:** Strict UTF-8 validation, +91 phone formatting, deduplication review, and identifier protection.
4. **Qualification Specialist:** Criteria rules, evidence attribution, objection defense, and tier assignment.

---

## 2. Live Context & Provider Truthfulness

- **Truthful Provider State:** System distinguishes between:
  - `HEURISTIC_FALLBACK`: Rule-based, bounded deterministic engine (zero cost, zero API keys required).
  - `MODEL_CONFIGURED_BUT_NOT_CALLED`: Key exists in environment but turn was answered via deterministic cache/rule.
  - `MODEL_CONNECTED_AND_CALLED`: Active external LLM call verified with recorded token expenditure.
- **Tenant RBAC Tools:** 10 bounded queries enforce workspace boundary (`ctx.assert_can_access_workspace`).
- **Exact Lead Lookup:** `AIToolRegistry.get_record_evidence()` requires exact `lead_id` lookup before falling back to domain matching, preventing cross-contamination between two people at the same domain.
- **Scope Reporting:** `get_lead_counts()` explicitly labels `query_scope: first_5000_in_vault` to avoid false full-corpus claims.

---

## 3. Persistent Filter Diff Approval (`app.js`)

When a user clicks **"Approve & Apply Filter Diff"** in the "Ask Discovery AI" panel:
- `apps/web/app.js::approveFilterDiff()` updates:
  - `state.leadMode`: Switches between `'people'` and `'organization'`.
  - `state.currentProfile.search_parameters`: Persists `target_occupations` and `geographic_affinities`.
  - `state.currentProfile.criteria_cards`: Persists structured targeting cards.
  - `localStorage`: Saves to `matrix_filter_plan_{client_id}` with timestamp for reload survival.
- Automatically triggers `applyDiscoveryFilters()` to re-render the table preview with the newly approved criteria immediately.
- If the user clicks **Reject / Dismiss**, state is preserved with zero changes.

---

## 4. Test Suite Evidence

- `tests/test_director_ai_specialists_and_evaluations.py`: All 10 evaluation scenarios pass locally (`10 passed in 2.21s`), verifying prompt injection defense, cross-tenant denial, and specialist routing.
