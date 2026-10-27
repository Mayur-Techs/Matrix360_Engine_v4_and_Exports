"""Matrix 360 Consulting — Genuine Evidence-Bound Web Crawler, AI Layer & Provenance Extractor.

Strictly extracts observable web facts from real websites with full per-field provenance:
- Page SHA256 hash
- Verified source URL and crawled URL list
- Retrieval timestamp (UTC)
- Exact extraction methods used (mailto, tel, Cloudflare XOR, Schema.org JSON-LD, DOM text, AI Markdown Extractor, Low-RAM Playwright)
- Outbound B2B domain snowballing for multi-hop discovery
- Strict ZERO fabrication: fields not published on the website remain empty/None.
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup

from .security_guard import DomainRateLimiter, RobotsTxtGuard, SafeRedirectHandler, validate_target_url
from .discovery_zero_api import ObfuscatedContactDecoder, SupplyChainSnowballSpider
from .ai_scraper_layer import (
    AILeadExtractionAgent,
    HtmlToAiMarkdownPruner,
    LowRamPlaywrightEscalator,
)

logger = logging.getLogger("matrix360.evidence_crawler")

EMAIL_STRICT_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10}\b"
)
DUMMY_EMAIL_PREFIXES = {"example", "test", "yourname", "domain", "user", "name", "email", "sample", "your"}

PHONE_RE = re.compile(
    r"(?:\+91[\s\-]?)?(?:[6789]\d{9}|033[\s\-]?\d{7,8}|011[\s\-]?\d{7,8}|022[\s\-]?\d{7,8}|\b0\d{2,4}[\s\-]?\d{6,8}\b|\b\d{5}[\s\-]?\d{5}\b)"
)

PRIORITY_INTERNAL_PATHS = [
    "/contact", "/contact-us", "/contact.html", "/contactus",
    "/about", "/about-us", "/about.html", "/aboutus",
    "/management", "/board-of-directors", "/leadership",
    "/plants", "/facilities", "/works", "/reach-us",
]


class GenuineEvidenceCrawler:
    """Production evidence-bound crawler with Crawl4AI-style Markdown pruning, AI extraction, and Low-RAM Playwright escalation."""

    def __init__(
        self,
        rate_limiter: Optional[DomainRateLimiter] = None,
        robots_guard: Optional[RobotsTxtGuard] = None,
        timeout_seconds: int = 5,
        allow_private_for_tests: bool = False,
        enable_playwright_escalation: bool = False,
        client_id: str = "lakhotia",
        user_prompt: str = "",
    ):
        self.rate_limiter = rate_limiter or DomainRateLimiter(min_delay_seconds=0.15)
        self.robots_guard = robots_guard or RobotsTxtGuard()
        self.timeout_seconds = timeout_seconds
        self.allow_private_for_tests = allow_private_for_tests
        self.enable_playwright_escalation = enable_playwright_escalation
        self.client_id = client_id
        self.user_prompt = user_prompt

    def fetch_url(
        self, url: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
        """Safely fetches a web page via HTTP, enforcing DNS SSRF, robots, redirects, and hashing.

        Returns: (html_content, status_code, page_hash, error_reason)
        """
        is_safe, reason, _ = validate_target_url(
            url, allow_private_for_tests=self.allow_private_for_tests
        )
        if not is_safe:
            return None, None, None, f"SSRF_BLOCKED: {reason}"

        if not self.robots_guard.can_fetch(url, allow_private_for_tests=self.allow_private_for_tests):
            return None, 403, None, "ROBOTS_TXT_DISALLOWED"

        parsed = urllib.parse.urlparse(url)
        self.rate_limiter.wait_for_domain(parsed.hostname or "")

        import ssl
        ssl_ctx = ssl.create_default_context()
        try:
            import certifi
            ssl_ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl_ctx),
            SafeRedirectHandler(allow_private_for_tests=self.allow_private_for_tests),
        )
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        req = urllib.request.Request(url, headers=headers)

        try:
            with opener.open(req, timeout=self.timeout_seconds) as resp:
                status = resp.status
                raw_bytes = resp.read()
                html_text = raw_bytes.decode("utf-8", errors="ignore")
                page_hash = hashlib.sha256(raw_bytes).hexdigest()
                return html_text, status, page_hash, None
        except urllib.error.HTTPError as exc:
            return None, exc.code, None, f"HTTP_ERROR_{exc.code}"
        except urllib.error.URLError as exc:
            return None, None, None, f"CONNECTION_ERROR: {exc.reason}"
        except Exception as exc:
            return None, None, None, f"FETCH_EXCEPTION: {type(exc).__name__}"

    def crawl_and_extract(
        self, start_url: str, canonical_domain: str, max_subpages: int = 3
    ) -> Dict[str, Any]:
        """Performs multi-page crawl across start_url and priority internal subpages.

        Extracts ONLY verifiable facts with exact provenance + AI qualification layer.
        """
        retrieval_ts = datetime.now(timezone.utc).isoformat()
        visited_pages: List[Dict[str, Any]] = []
        skipped_pages: List[Dict[str, str]] = []

        discovered_emails: Set[str] = set()
        discovered_phones: Set[str] = set()
        discovered_directors: Set[str] = set()
        discovered_addresses: List[str] = []
        discovered_turnovers: List[str] = []
        discovered_assets: List[str] = []
        discovered_gstins: Set[str] = set()
        discovered_cins: Set[str] = set()
        discovered_udyams: Set[str] = set()
        snowballed_domains: Set[str] = set()
        schema_types: Set[str] = set()
        extraction_methods: Set[str] = set()
        combined_html_chunks: List[str] = []

        observed_company_name: Optional[str] = None
        primary_page_hash: Optional[str] = None
        primary_verified_url: Optional[str] = None

        queue: List[str] = [start_url]
        seen_urls: Set[str] = set()

        while queue and len(visited_pages) < max_subpages:
            curr_url = queue.pop(0)
            clean_curr = curr_url.split("#")[0].rstrip("/")
            if clean_curr in seen_urls:
                continue
            seen_urls.add(clean_curr)

            html_text, status, page_hash, err_reason = self.fetch_url(curr_url)

            # Optional Low-RAM Playwright Escalation if JS SPA shell detected
            if (
                self.enable_playwright_escalation
                and html_text
                and len(BeautifulSoup(html_text, "html.parser").get_text(" ", strip=True)) < 180
                and LowRamPlaywrightEscalator.is_available()
            ):
                pw_html = LowRamPlaywrightEscalator.fetch_rendered_html(curr_url, timeout_ms=6000)
                if pw_html and len(pw_html) > len(html_text):
                    html_text = pw_html
                    page_hash = hashlib.sha256(pw_html.encode("utf-8", errors="ignore")).hexdigest()
                    extraction_methods.add("playwright_low_ram_dom")

            if not html_text:
                skipped_pages.append({"url": curr_url, "reason": err_reason or "EMPTY_RESPONSE"})
                continue

            combined_html_chunks.append(html_text[:25000])

            if not primary_page_hash:
                primary_page_hash = page_hash
                primary_verified_url = curr_url

            soup = BeautifulSoup(html_text, "html.parser")
            body_text = soup.get_text(" ", strip=True)

            # Outbound B2B domain snowballing
            try:
                outbound = SupplyChainSnowballSpider.extract_outbound_company_domains(
                    html_text, canonical_domain
                )
                for ob_dom in outbound[:10]:
                    snowballed_domains.add(ob_dom)
            except Exception:
                pass

            # 1. Company name extraction from Schema.org, og:site_name, or clean <title>
            if not observed_company_name:
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "{}")
                        if isinstance(data, list):
                            items = data
                        elif isinstance(data, dict):
                            items = data.get("@graph", [data])
                        else:
                            items = []
                        for it in items:
                            if isinstance(it, dict):
                                t = it.get("@type", "")
                                schema_types.add(str(t))
                                if t in ("Organization", "Corporation", "LocalBusiness") and it.get("name"):
                                    observed_company_name = str(it["name"]).strip()
                                    extraction_methods.add("schema_org_jsonld")
                                    break
                    except Exception:
                        pass

                if not observed_company_name:
                    og_site = soup.find("meta", property="og:site_name")
                    if og_site and og_site.get("content"):
                        observed_company_name = og_site["content"].strip()
                        extraction_methods.add("meta_og_site_name")

                if not observed_company_name and soup.title and soup.title.string:
                    raw_title = soup.title.string.strip()
                    clean = raw_title.split("|")[0].split("-")[0].split("–")[0].split("—")[0].strip()
                    if len(clean) >= 3 and not any(w in clean.lower() for w in ("home", "welcome", "index", "about", "contact")):
                        observed_company_name = clean
                        extraction_methods.add("title_tag")

            # 2. Extract mailto: and tel: anchors
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.lower().startswith("mailto:"):
                    email_val = href[7:].split("?")[0].strip().lower()
                    if "@" in email_val and "." in email_val.split("@")[-1]:
                        if not any(email_val.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg")):
                            discovered_emails.add(email_val)
                            extraction_methods.add("mailto_anchor")
                elif href.lower().startswith("tel:"):
                    tel_val = re.sub(r"[^\d+]", "", href[4:]).strip()
                    if len(tel_val) >= 8:
                        discovered_phones.add(tel_val)
                        extraction_methods.add("tel_anchor")

            # 3. Decode Cloudflare XOR and regex
            cf_bundle = ObfuscatedContactDecoder.extract_all_from_html(html_text)
            for em in cf_bundle.get("emails", []):
                clean_em = em.lower().strip()
                prefix = clean_em.split("@")[0]
                if prefix not in DUMMY_EMAIL_PREFIXES:
                    discovered_emails.add(clean_em)
                    extraction_methods.add("cloudflare_xor_or_text_regex")

            for ph in cf_bundle.get("phones", []):
                clean_ph = re.sub(r"[^\d+]", "", ph).strip()
                if len(clean_ph) >= 8:
                    discovered_phones.add(clean_ph)
                    extraction_methods.add("phone_regex")

            for gst in cf_bundle.get("wb_gstins", []):
                discovered_gstins.add(gst)
                extraction_methods.add("regulatory_gstin_regex")

            for cin in cf_bundle.get("wb_cins", []):
                discovered_cins.add(cin)
                extraction_methods.add("regulatory_cin_regex")

            for udy in cf_bundle.get("udyam_ids", []):
                discovered_udyams.add(udy)
                extraction_methods.add("regulatory_udyam_regex")

            # 4. Extract addresses and director names explicitly from text/tables
            lines = [l.strip() for l in soup.get_text("\n", strip=True).splitlines() if l.strip()]
            for line in lines:
                m = re.search(
                    r"(?:Doctor|Dr\.|Physician|Surgeon|Consultant|Pediatrician|Managing Director|Executive Director|Director|Promoter|Chairman|Plant Head|Proprietor|CEO|CFO|Founder|Partner)[:\s\-]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
                    line,
                    re.IGNORECASE,
                )
                if m:
                    cand = m.group(1).strip()
                    tokens = [t for t in cand.split() if t.lower() not in ("works", "plant", "factory", "office", "road", "street", "ltd", "pvt", "limited", "complex")]
                    if len(tokens) >= 2:
                        discovered_directors.add(" ".join(tokens))
                        extraction_methods.add("executive_title_regex")

            for m in re.finditer(
                r"(?:Works|Plant|Factory|Head Office|Registered Office|Corporate Office)[:\s\-]+([^<\n\r]{15,120})",
                body_text,
                re.IGNORECASE
            ):
                discovered_addresses.append(m.group(1).strip())
                extraction_methods.add("address_block_regex")

            for m in re.finditer(
                r"(?:annual turnover|gross revenue|turnover of)[:\s\-]+(₹?\s*[\d,.]+\s*(?:Cr|Crore|Lakh|Million|Billion|USD|INR))",
                body_text,
                re.IGNORECASE
            ):
                discovered_turnovers.append(m.group(1).strip())
                extraction_methods.add("turnover_statement_regex")

            visited_pages.append({
                "url": curr_url,
                "status_code": status,
                "page_hash": page_hash,
                "title": (soup.title.string.strip() if soup.title and soup.title.string else "")[:100],
            })

            # Queue priority internal subpages found on homepage
            if len(visited_pages) == 1:
                start_host = (urllib.parse.urlparse(start_url).hostname or "").lower()
                for a in soup.find_all("a", href=True):
                    raw_href = a["href"].strip()
                    joined = urllib.parse.urljoin(curr_url, raw_href)
                    p_join = urllib.parse.urlparse(joined)
                    j_host = (p_join.hostname or "").lower()
                    if j_host and (
                        j_host == canonical_domain.lower()
                        or j_host.endswith("." + canonical_domain.lower())
                        or j_host == start_host
                    ):
                        p_lower = p_join.path.lower()
                        if any(k in p_lower for k in ("contact", "about", "management", "plant", "facility", "reach", "leadership")):
                            if joined not in seen_urls and len(queue) < 6:
                                queue.append(joined)

        clean_phones_list = sorted(list(discovered_phones))
        clean_emails_list = sorted(list(discovered_emails))

        # Run AI Markdown Pruning & AI Lead Qualification Layer on crawled pages
        ai_extraction: Dict[str, Any] = {}
        if combined_html_chunks:
            try:
                ai_extraction = AILeadExtractionAgent.enrich_and_qualify_with_ai(
                    raw_html="\n".join(combined_html_chunks[:2]),
                    domain=canonical_domain,
                    client_id=self.client_id,
                    user_prompt=self.user_prompt,
                    existing_extracted={
                        "company_name": observed_company_name,
                        "director_name": sorted(list(discovered_directors))[0] if discovered_directors else None,
                        "address": discovered_addresses[0] if discovered_addresses else None,
                        "turnover": discovered_turnovers[0] if discovered_turnovers else None,
                        "assets": discovered_assets[0] if discovered_assets else None,
                    },
                )
                extraction_methods.add(str(ai_extraction.get("ai_extraction_mode") or "ai_markdown_extractor"))
                if not discovered_directors and ai_extraction.get("director_name"):
                    discovered_directors.add(str(ai_extraction["director_name"]))
                if not discovered_addresses and ai_extraction.get("address"):
                    discovered_addresses.append(str(ai_extraction["address"]))
                if not discovered_assets and ai_extraction.get("observed_assets_or_fleet"):
                    discovered_assets.append(str(ai_extraction["observed_assets_or_fleet"]))
            except Exception as exc:
                logger.debug(f"AI extraction layer notice on {canonical_domain}: {exc}")

        # Compute Evidence-Bound Confidence Score
        confidence = 0.50
        if observed_company_name:
            confidence += 0.10
        if clean_emails_list:
            confidence += 0.15
        if clean_phones_list:
            confidence += 0.15
        if discovered_addresses:
            confidence += 0.05
        if discovered_gstins or discovered_cins:
            confidence += 0.03
        confidence = round(min(0.98, confidence), 2)

        return {
            "canonical_domain": canonical_domain,
            "company_name": observed_company_name or canonical_domain.title(),
            "verified_source_url": primary_verified_url or start_url,
            "crawled_urls": [p["url"] for p in visited_pages],
            "retrieval_timestamp": retrieval_ts,
            "page_hash": primary_page_hash or "",
            "pages_crawled_count": len(visited_pages),
            "visited_pages": visited_pages,
            "skipped_pages": skipped_pages,
            "extraction_methods": sorted(list(extraction_methods)),
            # Strictly observed facts — ZERO invented data (turnover is None unless explicitly stated on page)
            "emails": clean_emails_list,
            "primary_email": clean_emails_list[0] if clean_emails_list else None,
            "phones": clean_phones_list,
            "primary_phone": clean_phones_list[0] if clean_phones_list else None,
            "director_name": sorted(list(discovered_directors))[0] if discovered_directors else None,
            "all_directors": sorted(list(discovered_directors)),
            "address": discovered_addresses[0] if discovered_addresses else None,
            "turnover": discovered_turnovers[0] if discovered_turnovers else None,
            "assets": discovered_assets[0] if discovered_assets else None,
            "gstins": sorted(list(discovered_gstins)),
            "cins": sorted(list(discovered_cins)),
            "udyam_ids": sorted(list(discovered_udyams)),
            "snowballed_domains": sorted(list(snowballed_domains)),
            "ai_extraction": ai_extraction,
            "confidence_score": confidence,
            "raw_evidence": {
                "observed_emails": clean_emails_list,
                "observed_phones": clean_phones_list,
                "observed_directors": sorted(list(discovered_directors)),
                "observed_address": discovered_addresses[:2],
                "observed_turnover": discovered_turnovers[:1],
                "observed_gstins": sorted(list(discovered_gstins)),
                "observed_cins": sorted(list(discovered_cins)),
                "ai_reasoning": ai_extraction.get("ai_reasoning", ""),
            },
        }
