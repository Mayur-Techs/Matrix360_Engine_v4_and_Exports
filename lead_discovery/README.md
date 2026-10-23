# LeadScope AI Studio v3.0 — Zero-API 500 to 5,000 Lead Discovery & Playwright Extraction Engine

## 100% Zero-API Discovery Mode Enabled by Default (No Serper API Required!)

This FastAPI + Playwright multi-agent engine discovers, pre-qualifies, and extracts 500 to 5,000 B2B industrial leads **without Serper API, Google Paid Search API, or any paid scraping subscriptions**.

### The 8 Zero-API ("Unhinged" Multi-Vector OSINT) Discovery Engines (`discovery_zero_api.py`)

1. **Vector 1 — Keyless PIN-Code × Industrial Estate × Sector Dork Matrix (`KeylessSearchRotator`)**:
   - Combinatorially pairs **44 West Bengal Industrial PIN Codes** (`711302` Dhulagarh/Sankrail, `711411` Jalan Complex, `711310` Bauria, `711303` Uluberia, `712223` Dankuni, `712222` Baidyabati, `700088` Taratala/Hide Rd, `743504` Falta SEZ, etc.) × **20 Industrial Estates** × **24 Sector Signatures** (`"cast iron foundry"`, `"3PL warehouse"`, `"steel forging"`, `"packaging pvt ltd"`, `"UDYAM-"`, `"GSTIN 19"`) into **650 to 1,680+ targeted search dorks**.
   - Executes directly against **DuckDuckGo Lite (`lite.duckduckgo.com`)**, **DuckDuckGo HTML (`html.duckduckgo.com`)**, **Bing HTML**, and **Public SearXNG instances**, with automatic Playwright headless search fallback.
2. **Vector 2 — OpenStreetMap Overpass QL Industrial Polygon & Geo-Tag Harvester (`OverpassIndustrialHarvester`)**:
   - Queries `https://overpass-api.de/api/interpreter` (100% free, no API key) for every polygon/node tagged `landuse=industrial`, `building=industrial`, `building=warehouse`, `man_made=works`, and `office=company` across Howrah, Hooghly, and Kolkata bounding boxes.
3. **Vector 3 — Public SSL Certificate Transparency Harvester (`CrtShHarvester`)**:
   - Queries `https://crt.sh/?q=%25keyword%25&output=json` to harvest every live `.in`, `.co.in`, and `.com` SSL certificate containing regional or industrial keywords (`howrah`, `hooghly`, `kolkata`, `foundry`, `forging`, `sankrail`, `dankuni`, `warehousing`).
4. **Vector 4 — Trade Association & Industrial Estate Allottee Roster Spider (`SupplyChainSnowballSpider`)**:
   - Crawls member rosters from trade bodies (`taasaofficial.com`, `howrahfoundryassociation.co.in`, EEPC India, WBIDC industrial parks, Falta SEZ unit lists) to extract official member domains while excluding the directory portal itself from buyer leads.
5. **Vector 5 — CommonCrawl Index & Wayback Machine CDX Harvester (`ArchivalIndexHarvester`)**:
   - Queries `index.commoncrawl.org` and `web.archive.org/cdx/search/cdx` for `.co.in` and `.in` `/contact` and `/facilities` URLs at zero cost.
6. **Vector 6 — Supply-Chain Graph Snowball Spider & `/sitemap.xml` Deep Harvester**:
   - Snowballs 50 seed domains into 500–5,000 domains by extracting outbound vendor, client, sister-concern, and ancillary unit domains from `/clients`, `/vendors`, `/partners`, and `/sitemap.xml`.
7. **Vector 7 — Cloudflare `data-cfemail` XOR Hex Decoder & Regulatory ID Extractor (`ObfuscatedContactDecoder`)**:
   - Decodes Cloudflare-obfuscated emails (`data-cfemail` & `/cdn-cgi/l/email-protection#`) via bitwise XOR in Python without needing browser clicks, de-mangles `[at]` / `[dot]` and JS string concatenations, and extracts West Bengal GSTINs (`19...`), WB Corporate Identification Numbers (`CIN ...WB...`), and MSME `UDYAM-` numbers.
8. **Vector 8 — Two-Tier High-Concurrency Scale Pipeline (`HybridScaleOrchestrator`)**:
   - **Tier 1 (35x Async HTTP Workers)**: Blasts through static/SSR corporate sites in seconds.
   - **Tier 2 (5x Playwright Chromium Workers)**: Escalates React/Vue/Angular SPAs and lazy-loaded DOM footers to real headless/headful browser contexts.

## Quickstart (Zero API Keys Needed)

```bash
pip install -r requirements.txt
playwright install chromium

# Run the automated 7-test verification suite
python3 test_engine.py

# Start the FastAPI server
uvicorn main:app --reload --port 8000
```
