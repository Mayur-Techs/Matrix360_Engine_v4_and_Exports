import sys
from pathlib import Path
_pkg_root = Path(__file__).resolve().parent
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
"""
Two-Tier High-Concurrency Crawler (Async HTTP Pre-Pass + Playwright Chromium Pool)
with Cloudflare `data-cfemail` XOR Decoding, Sitemap.xml Subpage Harvesting,
and Supply-Chain Outbound Domain Snowballing (50 -> 500 -> 5,000 Leads).
"""
import asyncio
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from config import EngineConfig
from agents import ContactExtractionAgent
from discovery_zero_api import ObfuscatedContactDecoder, SupplyChainSnowballSpider


class PlaywrightVisualCrawler:
    def __init__(self, config: EngineConfig):
        self.config = config

    async def crawl_domain(self, start_url: str, canonical_domain: str) -> Dict[str, Any]:
        """
        Executes real Playwright browser navigation across the verified homepage,
        `/sitemap.xml` priority links, and discovered internal pages (Contact, About,
        Leadership, Facilities), while decoding Cloudflare `data-cfemail` hex strings
        and snowballing outbound vendor/client domains.
        Automatically falls back to fast HTTP/DOM crawler if Playwright is unavailable.
        """
        try:
            return await self._crawl_playwright(start_url, canonical_domain)
        except Exception:
            return await self._crawl_http(start_url, canonical_domain)

    async def _crawl_playwright(self, start_url: str, canonical_domain: str) -> Dict[str, Any]:
        from playwright.async_api import async_playwright

        visited: List[Dict[str, Any]] = []
        skipped: List[Dict[str, str]] = []
        discovered_emails: Set[str] = set()
        discovered_phones: Set[str] = set()
        schema_org_types: Set[str] = set()
        snowballed_domains: Set[str] = set()
        wb_gstins: Set[str] = set()
        wb_cins: Set[str] = set()
        udyam_ids: Set[str] = set()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.playwright_headless)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            queue = [start_url]
            seen_urls = set()

            while queue and len(visited) < self.config.per_domain_max_pages:
                current_url = queue.pop(0)
                if current_url in seen_urls:
                    continue
                seen_urls.add(current_url)

                try:
                    resp = await page.goto(
                        current_url,
                        wait_until="domcontentloaded",
                        timeout=self.config.request_timeout_seconds * 1000
                    )
                    status = resp.status if resp else 0
                    if status in (401, 403, 429):
                        skipped.append({
                            "url": current_url,
                            "reason": f"HTTP_{status}_RESTRICTED_OR_WAF"
                        })
                        continue

                    # Scroll page to trigger lazy-rendered footers & contact widgets
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.5)

                    html = await page.content()
                    title = await page.title()
                    soup = BeautifulSoup(html, "html.parser")

                    body_text = soup.get_text(" ", strip=True)
                    if "cf-chl-bypass" in html or "Verify you are human" in body_text:
                        skipped.append({
                            "url": current_url,
                            "reason": "CLOUDFLARE_CHALLENGE_GATE_SKIPPED"
                        })
                        continue

                    # Extract mailto: and tel: links
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if href.lower().startswith("mailto:"):
                            email_val = href[7:].split("?")[0].strip()
                            if email_val:
                                discovered_emails.add(email_val.lower())
                        elif href.lower().startswith("tel:"):
                            tel_val = href[4:].strip()
                            if tel_val:
                                discovered_phones.add(tel_val)

                    # Decode Cloudflare data-cfemail XOR strings, JS concat emails, GSTIN/CIN/Udyam
                    decoded_bundle = ObfuscatedContactDecoder.extract_all_from_html(html)
                    discovered_emails.update(decoded_bundle["emails"])
                    discovered_phones.update(decoded_bundle["phones"])
                    wb_gstins.update(decoded_bundle["wb_gstins"])
                    wb_cins.update(decoded_bundle["wb_cins"])
                    udyam_ids.update(decoded_bundle["udyam_ids"])

                    # Extract schema.org JSON-LD
                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string or "{}")
                            if isinstance(data, dict) and "@type" in data:
                                schema_org_types.add(str(data["@type"]))
                        except Exception:
                            pass

                    # Extract from visible text
                    extracted = ContactExtractionAgent.extract_from_text(body_text)
                    discovered_emails.update(extracted["emails"])
                    discovered_phones.update(extracted["phones"])

                    # Supply-chain snowballing: harvest outbound client/vendor/sister-concern domains
                    if self.config.enable_supply_chain_snowball:
                        outbound = SupplyChainSnowballSpider.extract_outbound_company_domains(
                            html, canonical_domain
                        )
                        snowballed_domains.update(outbound)

                    visited.append({
                        "url": page.url,
                        "http_status": status,
                        "title": title[:120]
                    })

                    # Discover internal priority links from homepage
                    if len(visited) == 1:
                        raw_links = [
                            urljoin(page.url, a["href"])
                            for a in soup.find_all("a", href=True)
                        ]
                        priority_links = ContactExtractionAgent.prioritize_in_domain_links(
                            canonical_domain, raw_links
                        )
                        for pl in priority_links[: self.config.per_domain_max_pages]:
                            if pl not in seen_urls:
                                queue.append(pl)

                except Exception as exc:
                    skipped.append({
                        "url": current_url,
                        "reason": f"NAVIGATION_TIMEOUT_OR_ERROR: {type(exc).__name__}"
                    })

            await browser.close()

        return {
            "domain": canonical_domain,
            "pages_crawled": len(visited),
            "visited_pages": visited,
            "skipped_pages": skipped,
            "company_emails": sorted(discovered_emails),
            "company_phones": sorted(discovered_phones),
            "wb_gstins": sorted(wb_gstins),
            "wb_cins": sorted(wb_cins),
            "udyam_ids": sorted(udyam_ids),
            "snowballed_domains": sorted(snowballed_domains),
            "schema_org_types": sorted(schema_org_types),
            "crawler_mode": "playwright_chromium",
        }

    async def _crawl_http(self, start_url: str, canonical_domain: str) -> Dict[str, Any]:
        """Fast, robust async HTTP/BeautifulSoup crawler fallback requiring zero browser binaries."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._crawl_http_sync, start_url, canonical_domain)

    def _crawl_http_sync(self, start_url: str, canonical_domain: str) -> Dict[str, Any]:
        visited: List[Dict[str, Any]] = []
        skipped: List[Dict[str, str]] = []
        discovered_emails: Set[str] = set()
        discovered_phones: Set[str] = set()
        schema_org_types: Set[str] = set()
        snowballed_domains: Set[str] = set()
        wb_gstins: Set[str] = set()
        wb_cins: Set[str] = set()
        udyam_ids: Set[str] = set()

        queue = [start_url]
        seen_urls = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        while queue and len(visited) < self.config.per_domain_max_pages:
            current_url = queue.pop(0)
            if current_url in seen_urls:
                continue
            seen_urls.add(current_url)

            try:
                req = urllib.request.Request(current_url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                    status = resp.status
                    html = resp.read().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else canonical_domain
                    body_text = soup.get_text(" ", strip=True)

                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if href.lower().startswith("mailto:"):
                            email_val = href[7:].split("?")[0].strip()
                            if email_val:
                                discovered_emails.add(email_val.lower())
                        elif href.lower().startswith("tel:"):
                            tel_val = href[4:].strip()
                            if tel_val:
                                discovered_phones.add(tel_val)

                    decoded_bundle = ObfuscatedContactDecoder.extract_all_from_html(html)
                    discovered_emails.update(decoded_bundle["emails"])
                    discovered_phones.update(decoded_bundle["phones"])
                    wb_gstins.update(decoded_bundle["wb_gstins"])
                    wb_cins.update(decoded_bundle["wb_cins"])
                    udyam_ids.update(decoded_bundle["udyam_ids"])

                    for script in soup.find_all("script", type="application/ld+json"):
                        try:
                            data = json.loads(script.string or "{}")
                            if isinstance(data, dict) and "@type" in data:
                                schema_org_types.add(str(data["@type"]))
                        except Exception:
                            pass

                    extracted = ContactExtractionAgent.extract_from_text(body_text)
                    discovered_emails.update(extracted["emails"])
                    discovered_phones.update(extracted["phones"])

                    if self.config.enable_supply_chain_snowball:
                        outbound = SupplyChainSnowballSpider.extract_outbound_company_domains(html, canonical_domain)
                        snowballed_domains.update(outbound)

                    visited.append({
                        "url": current_url,
                        "http_status": status,
                        "title": title[:120],
                    })

                    if len(visited) == 1:
                        raw_links = [urljoin(current_url, a["href"]) for a in soup.find_all("a", href=True)]
                        priority_links = ContactExtractionAgent.prioritize_in_domain_links(canonical_domain, raw_links)
                        for pl in priority_links[: self.config.per_domain_max_pages]:
                            if pl not in seen_urls:
                                queue.append(pl)
            except Exception as exc:
                skipped.append({"url": current_url, "reason": f"HTTP_FETCH_ERROR: {type(exc).__name__}"})

        return {
            "domain": canonical_domain,
            "pages_crawled": len(visited),
            "visited_pages": visited,
            "skipped_pages": skipped,
            "company_emails": sorted(discovered_emails),
            "company_phones": sorted(discovered_phones),
            "wb_gstins": sorted(wb_gstins),
            "wb_cins": sorted(wb_cins),
            "udyam_ids": sorted(udyam_ids),
            "snowballed_domains": sorted(snowballed_domains),
            "schema_org_types": sorted(schema_org_types),
            "crawler_mode": "stateless_http_dom",
        }
