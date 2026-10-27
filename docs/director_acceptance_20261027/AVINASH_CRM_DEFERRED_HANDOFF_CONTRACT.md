# Avinash CRM Deferred Handoff Contract

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Handoff Target:** Avinash CRM Core  
**Director Release Decision:** CRM IMPORT DEFERRED — HANDOFF PACKAGE READY LATER  
**Contract Version:** `audience-export.v1`  
**Date:** 27 October 2026  

---

## 1. Director's Clarification & Delivery Status

In strict accordance with the Director's clarified directive:
- **Mayur is NOT blocked by Avinash's CRM timeline.**
- **No active network transfer or CRM PostgreSQL database write is executed.**
- Endpoints `POST /api/v1/handoff` and `POST /api/v1/handoff/prepare` return truthful package readiness:
  - `status`: `"ready_for_handoff"`
  - `crm_stage`: `"CRM_IMPORT_DEFERRED"`
  - `external_receiver_connected`: `false`
  - `idempotency_hash`: SHA-256 cryptographic manifest checksum
  - `export_artifact_ready`: `true`

---

## 2. `audience-export.v1` JSON Contract Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Matrix360AudienceExportPackage",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "package_id",
    "client_id",
    "workspace_id",
    "snapshot_version",
    "export_timestamp",
    "manifest_checksum",
    "leads"
  ],
  "properties": {
    "package_id": { "type": "string" },
    "client_id": { "type": "string" },
    "workspace_id": { "type": "string" },
    "snapshot_version": { "type": "string" },
    "export_timestamp": { "type": "string", "format": "date-time" },
    "manifest_checksum": { "type": "string", "pattern": "^[a-f0-9]{64}$" },
    "leads": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["lead_id", "company_name", "canonical_domain", "qualification_tier", "source"],
        "properties": {
          "lead_id": { "type": "string" },
          "company_name": { "type": "string" },
          "canonical_domain": { "type": "string" },
          "named_contact": { "type": "string" },
          "role": { "type": "string" },
          "phone": { "type": "string" },
          "email": { "type": "string" },
          "catchment_district": { "type": "string" },
          "qualification_tier": { "type": "string", "enum": ["A", "B", "C", "PREPASS", "REVIEW", "EXCLUDE"] },
          "confidence_score": { "type": "number" },
          "source": { "type": "string" },
          "verified_source_url": { "type": "string" },
          "marketing_consent_verified": { "type": "boolean" },
          "crm_stage": { "type": "string" }
        }
      }
    }
  }
}
```

---

## 3. Mock Consumer Verification

Tested in `tests/test_crm_mock_consumer_contract.py`:
1. **Schema Compliance:** Successfully generates and validates `audience-export.v1` structures.
2. **Tamper Detection:** If any lead attribute or extra record is injected, SHA-256 checksum reconciliation fails immediately.
3. **Tenant Isolation:** Cross-tenant handoff requests are denied with `403 Forbidden`.
4. **Offline Isolation:** Proven to operate with zero dependencies on live Avinash CRM webhooks or database connections.
