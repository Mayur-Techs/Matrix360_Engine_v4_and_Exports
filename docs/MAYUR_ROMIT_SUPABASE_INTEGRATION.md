# MATRIX 360 — MAYUR & ROMIT DATA PIPELINE INTEGRATION
**Date:** 26 October 2026  
**Authors:** Mayur (Web/Data Architecture) & Romit (Google Maps Scraper V4)  
**Status:** Unified, Integrated & Verified  

---

## 1. Overview & Architectural Convergence

Mayur's workstream (Universal Web Evidence Crawler, 2.3M Large-Scale Engine, Multi-Client Qualification) and Romit's workstream (Google Maps Scraper V4) have been unified into a single canonical data pipeline. 

Previously, Romit's Maps Scraper operated as an isolated sidecar emitting independent JSON exports, while Mayur's Web Crawler populated `ProductionLeadVault`. With the implementation of `lead_discovery/maps_adapter.py`, leads from both sources now flow seamlessly into a shared SQLite WAL database and Supabase PostgreSQL instance with full source attribution, cross-source deduplication, and unified multi-tier qualification.

---

## 2. Shared Canonical Data Flow Architecture

```
[Mayur Web Evidence Crawler]             [Romit Google Maps Scraper V4]
   (live_evidence_crawler)                     (maps_scraper_v4)
              │                                        │
              │                                        ▼
              │                           [lead_discovery/maps_adapter.py]
              │                              - extract_canonical_domain()
              │                              - clean_phone() [text string]
              │                              - normalize_maps_record()
              │                              - exact cross-source deduplication
              ▼                                        ▼
     ┌────────────────────────────────────────────────────────┐
     │       ProductionLeadVault (SQLite WAL Engine)          │
     │       - Client Scoping (client_id)                     │
     │       - Job Scoping (job_id)                           │
     │       - Source Attribution (source)                    │
     └────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                     [Supabase Dual-Sync Engine]
                                 │
                                 ▼
                    [Avinash CRM Core Pipeline]
```

---

## 3. Schema Normalization & Mapping

Romit's Google Maps Scraper exports records adhering to the `matrix360-lead-export.v1` schema. The `RomitMapsAdapter.normalize_maps_record` method maps this schema into the canonical Matrix 360 lead entity:

| Romit Maps Field | Canonical Lead Field | Transformation Applied |
|---|---|---|
| `company.name` / `business_name` | `company_name`, `company` | Strip excess whitespace, preserve corporate name. |
| `company.website` / `evidence.official_website` | `canonical_domain`, `domain` | `extract_canonical_domain()` removes `www.`, protocols, and port numbers. |
| `contacts[0].name` / `dm_name` | `director_name`, `named_contact` | Decision maker name or fallback to "Management". |
| `contacts[0].role` / `dm_role` | `role` | "Chief Medical Officer", "Managing Director", etc. |
| `contacts[0].phone` / `phone` | `phone`, `company_phone` | `clean_phone()` enforces text string format (`+91 98...`) preventing numeric scientific notation. |
| `contacts[0].email` / `email` | `email`, `company_email` | Lowercased string. |
| `company.address` / `location` | `address`, `district` | Detects catchment district (Chandannagar, Howrah, Hooghly, Nadia). |
| `evidence.provider_place_id` | `verified_source_url` | Google Maps Place URL or official website URL. |
| *(hardcoded tag)* | `source` | Strictly labeled `"maps_scraper_v4"`. |

---

## 4. Cross-Source Deduplication Logic

When records are ingested via `POST /api/discovery/ingest-maps`, `RomitMapsAdapter.ingest_records()` checks the database for existing records under the target `client_id`:
1. **Domain Deduplication:** If the canonical domain matches an existing record (e.g. from the web crawler), the record is merged/updated rather than creating a duplicate row.
2. **Phone Deduplication:** If the cleaned phone string matches an existing record, the provenance evidence is updated.
3. **Deduplication Reporting:** The API returns `{"saved_and_persisted": X, "duplicates_deduplicated": Y}` for complete operator transparency.

---

## 5. API Endpoints

### 5.1. `POST /api/discovery/ingest-maps`
Ingests a batch of Google Maps leads from Romit's scraper into the target client workspace:
* **Request Body:**
  ```json
  {
    "client_id": "shree",
    "records": [ ... ]
  }
  ```
* **Response:**
  ```json
  {
    "status": "success",
    "client_id": "shree",
    "total_submitted": 3,
    "saved_and_persisted": 3,
    "duplicates_deduplicated": 0,
    "source": "maps_scraper_v4"
  }
  ```

### 5.2. `GET /api/discovery/sources-summary`
Returns origin breakdown for any client workspace:
* **Response:**
  ```json
  {
    "client_id": "shree",
    "total_leads": 12,
    "by_source": {
      "live_evidence_crawler": 7,
      "maps_scraper_v4": 5
    }
  }
  ```

---

## 6. End-to-End Test Verification

The integration was verified by automated acceptance tests in `tests/test_director_4_acceptance_tests.py::test_acceptance_test_3_source_convergence`:
* Verified successful ingestion of Romit Maps records into `ProductionLeadVault`.
* Verified exact deduplication when identical records are re-submitted.
* Verified origin breakdown returns accurate counts for both `maps_scraper_v4` and `live_evidence_crawler`.
