# MATRIX 360 — AVINASH CRM INTEGRATION & GATEWAY CONTRACT
**Directory:** `docs/director_acceptance_20261027/09_AVINASH_CRM_CONTRACT.md`  
**Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Collaborator:** Avinash (CRM & Tenant Boundary Code Owner)  
**Status:** **CONTRACT SPECIFIED & GATEWAY VERIFIED**  

---

## 1. Integration Boundary & Ownership Principles

In strict adherence to the project governance rules:
1. **Avinash's CRM is the Single Customer-Facing Shell:** Mayur's backend engine serves as a private, high-performance intelligence and data-processing service.
2. **Server-to-Server Signed Gateway:** Browser clients never communicate directly with Mayur's Render engine using service-role keys or credentials. All CRM requests flow from Avinash's backend to Mayur's gateway via signed HMAC assertions.
3. **Dynamic Business Onboarding Preserved:** Workspaces are dynamically provisioned in Avinash's CRM. Mayur's engine accepts arbitrary client IDs without requiring hardcoded preset mappings.
4. **No Direct Marketing Sending:** This engine produces qualified audience evidence and approved handoff candidates. It does **not** own marketing senders, WhatsApp bots, or email dispatchers.

---

## 2. Gateway Authentication Contract

### 2.1. Request Signature Specification
Requests sent from Avinash's CRM backend to Mayur's service must include four signed headers:

```http
X-Matrix-Workspace: {client_workspace_id}
X-Matrix-Timestamp: {epoch_seconds}
X-Matrix-Nonce: {cryptographic_nonce_16_to_128_chars}
X-Matrix-Signature: {sha256_hmac_hex}
```

The signed payload is computed as:
$$\text{payload} = \text{"v1\textbackslash n"} + \text{METHOD} + \text{"\textbackslash n"} + \text{PATH} + \text{"\textbackslash n"} + \text{WORKSPACE} + \text{"\textbackslash n"} + \text{TIMESTAMP} + \text{"\textbackslash n"} + \text{NONCE}$$

### 2.2. Single-Use Nonce & Clock Skew Guard
* **Max Allowed Age:** 300 seconds (`SERVICE_AUTH_MAX_AGE_SECONDS = 300`).
* **Single-Use Nonce:** Every nonce is stored in `runtime/metadata.sqlite` via `services.api.store.consume_service_nonce`. Replay attempts with an identical nonce immediately fail with `HTTP 401 Unauthorized`.

---

## 3. CRM Handoff Contract (`POST /api/v1/handoff`)

When an operator approves an audience shortlist in the UI and clicks **[Handoff to Avinash CRM]**, the engine executes an idempotent handoff:

### 3.1. Request Payload Schema
```json
{
  "client_id": "shree",
  "snapshot_version": "v1.2.0",
  "handoff_target": "Avinash_CRM_Core",
  "lead_count": 2,
  "leads": [
    {
      "lead_id": "shree:drsmukherjee-chd.org",
      "company_name": "Dr. Subhashis Mukherjee Clinic",
      "canonical_domain": "drsmukherjee-chd.org",
      "named_contact": "Dr. Subhashis Mukherjee",
      "role": "Chief Medical Officer / Physician",
      "phone": "+91 98310 44219",
      "email": "dr@mukherjee.org",
      "district": "Chandannagar",
      "source": "maps_scraper_v4",
      "qualification_tier": "A",
      "fit_reasoning": "Senior medical practitioner with high purchasing capacity indicator.",
      "verified_source_url": "https://drsmukherjee-chd.org"
    }
  ]
}
```

### 3.2. Response Schema
```json
{
  "status": "success",
  "client_id": "shree",
  "synced_leads": 2,
  "crm_destination": "Avinash PostgreSQL Pipeline",
  "idempotency_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 4. Verification Tests

Verified in automated test suites:
1. `tests/test_service_gateway_auth.py::test_gateway_request_is_workspace_scoped_and_single_use` -> **PASSED**
2. `tests/test_service_gateway_auth.py::test_gateway_signature_cannot_be_reused_for_another_path` -> **PASSED**
3. `tests/test_campaign_routes.py::test_campaign_api_lifecycle_and_shortfall` -> **PASSED**
