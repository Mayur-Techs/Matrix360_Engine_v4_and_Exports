# MATRIX 360 — DIRECTOR DEMO WALKTHROUGH & SCRIPT
**Presentation Date:** 27 October 2026  
**Demonstrator:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Target Audience:** Director & Executive Stakeholders  

---

## 1. Executive Demonstration Objective

Demonstrate that Matrix 360 is a fully operational, AI-native business intelligence and customer acquisition engine. Show that an operator can explain a commercial objective in natural language and receive verified, qualified, explainable lead intelligence that flows into the CRM and marketing ecosystem with zero synthetic records.

---

## 2. Step-by-Step Live Demonstration Script

### Step 1: Workspace Selection & Dynamic Client Adaptation
1. Open the Matrix 360 application at `http://localhost:8000` or the authorized demo URL.
2. Observe the top workspace indicator: Currently set to **Lakhotia Industrial Complex**.
3. Point out that the system has automatically initialized into **Organization Mode** (`🏢 Org Mode`).
4. Point out the Smart Filter Pills: Specifically tailored to Lakhotia: *Manufacturing*, *Logistics / 3PL*, *Steel & Foundry*, *₹10 Cr – ₹50 Cr*, *Managing Director*.
5. In the Client Brand dropdown, switch to **Shree Heights (Chandannagar Luxury Residential)**:
   * **Visual Result:** Watch the system dynamically flip to **People Mode** (`👥 People Mode`).
   * **Pills Update:** The smart filter pills instantly re-render with Shree Heights criteria: *Doctor / Clinic*, *Chartered Accountant*, *Advocate / Lawyer*, *Senior CXO / VP*, *Chandannagar Resident*.
   * **Prompt Updates:** The AI Discovery Prompt updates to: *"High-income individuals, senior professionals, doctors, CAs, and business owners in Chandannagar and Hooghly"*.

### Step 2: Three Distinct Criteria Sections (Section A, B, C)
1. Scroll to the **Three Criteria Cards** directly above the leads tables:
   * **Section A (Search Parameters):** Displays target professions (Doctors, CAs, Advocates), target geographies (Chandannagar, Hooghly), and affinity rules.
   * **Section B (Qualification Parameters):** Displays budget capacity requirement (₹70L+ apartment budget), space fit (3BHK/4BHK riverfront luxury), and decision-maker roles.
   * **Section C (AI Evaluation Criteria):** Displays AI assessment focus, 85% confidence gate, and explicit proxy policy.
2. Explain to the Director: *"Scraping search dorks and qualification evaluation are strictly separated into dedicated architectural blocks, preventing low-quality leads from entering the database."*

### Step 3: Conversational Strategy Refinement with AI
1. Locate the **AI Growth Advisor Card** (`#advisor-assistant-card`):
2. Type the following ordinary-language directive into the input box:
   > *"Also include senior pediatricians and corporate executives living in Bangalore with family roots in Chandannagar."*
3. Click **[Refine Targeting]**:
   * **Visual Result:** The AI assistant responds: *"Switched target entity to Individual Decision-Makers (People Mode). Expanded target audience to include Healthcare Practitioners. Added out-of-town geographic affinity rule for native executives working in major corporate hubs (Bangalore)."*
   * The discovery prompt and criteria update in real time.
4. Click **[Apply to Search & Crawl]**.

### Step 4: Romit Google Maps Scraper Ingestion & Source Convergence
1. Click the button **[📍 Ingest Romit Maps Leads]**:
   * **Visual Result:** Toast notification confirms: *"✅ Ingested 3 Google Maps leads (0 dups handled)."*
2. Look at **Table 1: Existing Database Leads**:
   * The table immediately populates with verified Chandannagar medical clinics and chartered accountant practices:
     * *Dr. B. C. Roy Diagnostic & Clinic Centre* (Dr. Subhashis Mukherjee)
     * *S. K. Banerjee & Associates* (CA Sougata Banerjee)
     * *Hooghly Riverfront Chambers* (Advocate Debabrata Roy)
   * Note the distinct origin badge: `<span class="pill">📍 Google Maps</span>`.
3. In the **Lead Source Filter** dropdown, switch from *All Sources* to *📍 Romit Google Maps Scraper* to filter exclusively by Maps records.

### Step 5: Live AI Web Crawler Execution & Dual Table Presentation
1. Click **[⚡ Discover Live Leads]**:
   * **Terminal Monitor:** The dark emerald crawler terminal slides down (`#live-crawler-desktop`).
   * **Speed Gauge:** Displays real-time crawling speed (~18.5 leads/min).
   * **Progress Bar:** Tracks discovered leads toward target count.
2. Look directly below Table 1 to observe **Table 2: Newly Generated Leads**:
   * Note the distinct lavender header: **Newly Generated Leads (Job: job_...)**.
   * Freshly scraped leads appear strictly in Table 2, preserving the persistent database records in Table 1 above.
   * Emphasize to the Director: *"Existing database records are never hidden or overwritten; new discoveries appear in an explicit second table directly below."*

### Step 6: Contextual Whole-Profile AI Qualification
1. On any lead row, click the **[Inspect]** button:
   * **Visual Result:** The **Lead Provenance & AI Qualification** modal opens.
2. Highlight the three key evaluation sections in the modal:
   * **Verified Contacts:** Phone number formatted cleanly as `+91 98310 44219` and verified corporate email.
   * **AI Qualification Assessment (Tier A):** Bullet points showing exact evidence (e.g. *"Senior medical practitioner with high purchasing capacity indicator"*).
   * **Open Uncertainties & Research Proxies:** Highlights with full intellectual honesty: *"Specific budget capacity is an evidenced research proxy; active buyer intent requires direct human engagement."*
3. Close the modal.

### Step 7: CRM Handoff & Multichannel Clean Exports
1. Click **[Handoff to Avinash CRM]**:
   * Toast notification confirms: *"✅ Successfully handed off leads to Avinash's CRM!"*
   * Data flows via authenticated `/api/v1/handoff` into Avinash's PostgreSQL pipeline.
2. Click **[💬 WhatsApp CSV]**:
   * Inspect the downloaded CSV in Excel or Notepad.
   * Point out that the phone column is formatted as `="+919831044219"`, preventing Excel from corrupting it into scientific notation (`9.83E+11`).

### Step 8: Truthful Zero Results & Empty State
1. In the search box, type an impossible query: `NonExistentFirmXYZ`.
2. Notice the table counter: *"Showing 0 verified records"*.
3. Explain to the Director: *"When real evidence does not exist, Matrix 360 truthfully displays zero leads. It never hallucinates fictitious businesses or synthetic contact numbers."*
