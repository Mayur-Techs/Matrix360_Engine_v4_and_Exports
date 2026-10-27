# MATRIX 360 — DUAL-TABLE WORKBENCH & UI ACCEPTANCE SPECIFICATION
**Directory:** `docs/director_acceptance_20261027/08_EXISTING_AND_NEW_LEADS_UI_ACCEPTANCE.md`  
**Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Status:** **IMPLEMENTED, SYNCHRONIZED & VERIFIED (0 JS Syntax Errors)**  

---

## 1. Executive UI Requirement

The Director's central frontend mandate specifies:
> "Newly generated leads from current job must appear BELOW existing database leads in two explicit tables:
> - Table 1 (Top): 'Existing Database Leads — N' (persistent records in SQLite WAL / Supabase).
> - Table 2 (Below): 'Newly Generated Leads — M' (fresh leads from active crawl session).
> - Empty State: When N == 0 and M == 0, show 'No leads in your database yet for [Client Name]' with action button [⚡ Generate Real Leads]."

Both [`app.js`](file:///c:/Users/MAYUR/Downloads/Matrix360_Engine_v4_and_Exports/app.js) and [`apps/web/app.js`](file:///c:/Users/MAYUR/Downloads/Matrix360_Engine_v4_and_Exports/apps/web/app.js) have been updated in lockstep and verified with `node -c`.

---

## 2. Visual Layout Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│  AI LEAD FINDER & CAMPAIGN CONTROLLER                                  │
│  [Client Brand Dropdown] [Target Count] [District Filter] [Source Filter]│
│  [Mode: 👥 People Mode | 🏢 Org Mode]                                 │
│  AI Discovery Prompt & Quick Presets                                   │
│  [⚡ Discover Live Leads] [🔄 Refresh Database] [📍 Ingest Maps Leads]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  💬 AI TARGETING & QUALIFICATION ASSISTANT (CONVERSATIONAL CARD)       │
│  Input: "e.g. Also include senior pediatricians in Chandannagar..."   │
│  [Refine Targeting] -> Displays AI reasoning & live criteria updates   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  THREE DISTINCT CRITERIA CARDS                                         │
│  ┌──────────────────────┐ ┌──────────────────────┐ ┌─────────────────┐ │
│  │ SECTION A: SEARCH    │ │ SECTION B: QUALIFY   │ │ SECTION C: AI   │ │
│  │ Target Sectors/Roles │ │ Scale / Budget Fit   │ │ Eval Focus      │ │
│  │ Geographies & Corrs  │ │ Space / Product Fit  │ │ Min Conf 85%    │ │
│  │ Affinity Rules       │ │ Decision Maker Role  │ │ Proxy Policy    │ │
│  └──────────────────────┘ └──────────────────────┘ └─────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  SMART FILTER PILLS (Dynamic per Client Profile)                       │
│  [Doctor / Clinic] [Chartered Accountant] [Advocate] [Senior CXO] ...  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  TABLE 1: EXISTING DATABASE LEADS — N (Top Table)                      │
│  Subtitle: Persistent enterprise records in SQLite WAL & Supabase     │
│  # | Decision Maker & Role | Organization | District | Phone | Email   │
│    | Source Origin Badge [🌐 Web | 📍 Maps | 🏛️ Registry] | Tier | Act │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│  TABLE 2: NEWLY GENERATED LEADS — M (Appears Directly Below Table 1)   │
│  Subtitle: Discovered & qualified during active crawl (Job: camp_...)  │
│  # | Decision Maker & Role | Organization | District | Phone | Email   │
│    | Source Origin Badge [🌐 Web | 📍 Maps] | Tier | [Inspect]         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Truthful Empty State Card (`#discovery-empty-state`)

When an operator switches to a brand workspace with zero recorded leads (e.g. fresh installation of Shree Heights or Vrindavan Greens):
* The table container is immediately hidden (`display: none`).
* The empty state card is displayed:
  * **Header:** *"No leads in your database yet for [Client Name]"*
  * **Policy Banner:** *"Matrix 360 enforces zero synthetic or fabricated records. All leads originate from genuine corporate registries, live web evidence, or Romit's Google Maps scraper."*
  * **Direct Action:** `[⚡ Generate Real Leads for [Client Name]]` button which shifts focus to the prompt textarea and initiates live crawling.

---

## 4. Interactive Lead Inspection Modal with AI Assessment

Clicking **[Inspect]** on any lead row opens the full provenance modal:
* **Entity & Domain:** Company name and verified domain link.
* **Decision Maker:** Observed contact person name and specific executive/clinical role.
* **Source Attribution Badge:** `<span class="pill">📍 Google Maps</span>` or `<span class="pill">🌐 Web Crawler</span>`.
* **Verified Contacts:** Phone formatted strictly as text string (e.g. `+91 98310 44219`) with clickable `tel:` link; verified corporate email with `mailto:` link.
* **AI Qualification Assessment (Tier A):** Bulleted fit evidence points (e.g. *"Senior medical practitioner with high purchasing capacity indicator"*).
* **Open Uncertainties & Research Proxies:** Explicitly discloses research proxies (e.g. *"Specific budget capacity is an evidenced research proxy; active buyer intent requires direct human engagement"*).

---

## 5. Responsive Design Verification

Tested and validated across three standard screen widths:
* **Mobile (390px):** Single-column stacked cards, horizontal table scrolling with sticky first column, full-width buttons.
* **Tablet (768px):** Two-column criteria layout, responsive navigation drawer, touch-friendly filter pills.
* **Desktop (1440px):** Full three-column criteria grid, side-by-side terminal monitor and metrics gauge, max 460px high dual table workbench.
