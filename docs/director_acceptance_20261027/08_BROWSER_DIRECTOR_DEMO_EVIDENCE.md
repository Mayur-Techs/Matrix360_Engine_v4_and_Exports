# 08 — Browser Demonstration Walkthrough & Evidence Flow

**Date:** 27 October 2026  
**Demonstrator:** Mayur (`Mayur-Techs`)  
**Scope:** Mayur Lead Generation & Audience Intelligence Engine  
**Evidence Standard:** Real DOM elements, truthful state indicators, zero fabricated leads.

---

## 1. 8–10 Minute Director Meeting Demonstration Flow

1. **Step 1: Workspace & Client Onboarding**
   - User logs in via secure session cookie (`matrix_session`).
   - Selects client (e.g. **Shree Heights Chandannagar** or **Lakhotia**).
   - Navigation clearly shows "Lead Discovery" workspace with truthful tenant context.
2. **Step 2: Source File Upload & Schema Preflight**
   - Uploads dataset file; server runs preflight analysis (`ChunkPartitionManager.analyze_source_preflight`).
   - Displays detected encoding (strict UTF-8), row count, candidate identifiers (Phone, GST/CIN), and cloud feasibility status (`FEASIBLE` / `PARTITIONED_STORAGE_REQUIRED`).
3. **Step 3: Natural Language Audience Objective & "Ask Discovery AI"**
   - User types objective into bottom "Ask Discovery AI" panel (e.g. *"Target medical specialists and clinic promoters within 15 km of Chandannagar for 3BHK luxury residences"*).
   - AI Assistant parses objective and generates a structured filter diff showing proposed occupation chips, geographic affinities, and entity mode (`people`).
4. **Step 4: Filter Diff Review & Persistent Approval**
   - User inspects proposed diff.
   - Clicks **"Approve & Apply Filter Diff"**.
   - Active criteria cards update, parameters persist to profile and `localStorage`, and table preview re-filters dynamically.
5. **Step 5: Inspecting People-First Entity Results**
   - Table displays verified people at organizations (e.g., Dr. Subhashis Mukherjee at Dr. B.C. Roy Diagnostic Centre).
   - Missing fields render honestly as `Unknown / Not Observed`, `Unidentified Organization`, or `Unspecified District`.
   - Tier badges render evidence-based `Tier A` or `Needs Review`.
6. **Step 6: Provenance & Evidence Modal**
   - User clicks **Inspect** button.
   - Modal renders verified source URL anchor if observed; displays `No verified URL anchor observed` if absent.
   - Fit reasoning clearly explains commercial alignment without inferring personal wealth, caste, or private assets.
7. **Step 7: Two-Table Separation**
   - **Table 1 (Top):** Existing persistent leads in database vault.
   - **Table 2 (Bottom):** Newly generated leads from current crawl session tagged with `current_job_id`.
   - If no fresh crawl was run, bottom table displays truthful empty state: *"No newly generated leads in this session yet."*
8. **Step 8: Verified Audience Export**
   - User clicks **"Download Audience Export"** or triggers handoff.
   - Generates cryptographically sealed, versioned `audience-export.v1` package with SHA-256 idempotency hash.
   - Status clearly shows `READY_FOR_HANDOFF` with truthful disclosure that live CRM import is deferred.
