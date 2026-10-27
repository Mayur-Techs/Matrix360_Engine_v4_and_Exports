# 07 — Audience Export Contract: Ready for Handoff, Delivery Deferred

**Date:** 27 October 2026  
**Module Owner:** Mayur (`Mayur-Techs`)  
**External Integration Boundary:** Avinash CRM Core (`Avinash_CRM_Core`)  
**Contract Version:** `audience-export.v1`  
**Components:** `services/api/app.py`, `tests/test_crm_mock_consumer_contract.py`

---

## 1. Director Clarification on Deferred CRM Delivery

Per the Director's explicit instruction:
- **Active CRM Delivery is DEFERRED:** Mayur's engine must **not** attempt live webhook delivery, direct database writes to Avinash's tables, or mark leads as "synced to CRM".
- **Handoff Packaging is ACTIVE & VERIFIED:** Mayur's engine provides a versioned, cryptographically sealed export package (`audience-export.v1`) that is downloadable, offline-testable, and tamper-evident.

---

## 2. API Contract Endpoints

### `POST /api/v1/handoff/prepare`
- Generates an immutable, offline-verifiable handoff package.
- Calculates SHA-256 idempotency hash across the canonical lead array.
- Generates a tamper-evident HMAC signature using the tenant secret.
- **Truthful Status Returned:**
  ```json
  {
    "status": "ready_for_handoff",
    "delivery_status": "CRM_IMPORT_DEFERRED",
    "external_receiver_connected": false,
    "snapshot_version": "v1.0.0",
    "idempotency_hash": "...",
    "lead_count": 1,
    "signature": "...",
    "disclaimer": "CRM integration is intentionally deferred. Handoff package is staged for future consumer import."
  }
  ```

### `POST /api/v1/handoff`
- Enforces strict tenant isolation (`tenant_id == user.tenant_id`).
- Returns honest `ready_for_handoff` and `CRM_IMPORT_DEFERRED`.
- Rejects unauthenticated or cross-tenant handoff requests with 401 / 403.

---

## 3. Mock Consumer Validation

A standalone mock consumer was implemented and verified in `tests/test_crm_mock_consumer_contract.py`:
- Successfully validates package schema and verifies HMAC signature.
- Detects and rejects tampered lead payloads (`TamperedPayloadError`).
- Rejects cross-tenant import attempts.
- All 3 tests pass locally with 0 warnings or failures.
