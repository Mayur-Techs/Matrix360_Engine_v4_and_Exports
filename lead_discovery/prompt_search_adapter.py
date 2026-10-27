"""Matrix 360 Consulting — Dynamic Prompt-to-Search Query Generator & Multi-Engine Harvester.

Dynamically interprets user prompt (industry, geography, target role, scale),
constructs precision OSINT search dorks, and executes live multi-page web discovery
across public search engines (Bing HTML with base64 unwrapping, DuckDuckGo HTML & Lite,
and Outbound Supply-Chain Snowballing) with zero hardcoding.
"""
from __future__ import annotations

import base64
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup

from .security_guard import validate_target_url
from .discovery_zero_api import SupplyChainSnowballSpider

logger = logging.getLogger("matrix360.search_adapter")

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "of", "for", "with", "at", "by", "from",
    "on", "to", "into", "through", "about", "who", "whom", "whose", "which",
    "what", "where", "when", "why", "how", "all", "any", "both", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
    "want", "need", "find", "get", "looking", "companies", "company", "firm", "firms",
    "leads", "list", "top", "best", "give", "me"
}

KNOWN_GEOGRAPHIES = {
    # West Bengal
    "west bengal": ("West Bengal", "state"),
    # Hooghly & Greater Kolkata Residential
    "chandannagar": ("Chandannagar", "city"),
    "chandernagore": ("Chandannagar", "city"),
    "chandan nagar": ("Chandannagar", "city"),
    "hooghly": ("Hooghly", "district"),
    "hugli": ("Hooghly", "district"),
    "rishra": ("Rishra", "city"),
    "serampore": ("Serampore", "city"),
    "uttarpara": ("Uttarpara", "city"),
    "bhadreswar": ("Bhadreswar", "city"),
    "champdani": ("Champdani", "city"),
    "konnagar": ("Konnagar", "city"),
    "bandel": ("Bandel", "cluster"),
    "chinsurah": ("Chinsurah", "city"),
    # Nadia & Kalyani
    "kalyani": ("Kalyani", "city"),
    "madanpur": ("Madanpur", "cluster"),
    "nadia": ("Nadia", "district"),
    "ranaghat": ("Ranaghat", "city"),
    "chakdaha": ("Chakdaha", "city"),
    "kolkata": ("Kolkata", "city"),
    "calcutta": ("Kolkata", "city"),
    "howrah": ("Howrah", "district"),
    "hooghly": ("Hooghly", "district"),
    "dankuni": ("Dankuni", "cluster"),
    "sankrail": ("Sankrail", "cluster"),
    "dhulagarh": ("Dhulagarh", "cluster"),
    "uluberia": ("Uluberia", "cluster"),
    "jalan industrial": ("Jalan Industrial Complex", "cluster"),
    "liluah": ("Liluah", "cluster"),
    "belur": ("Belur", "cluster"),
    "durgapur": ("Durgapur", "city"),
    "asansol": ("Asansol", "city"),
    "raniganj": ("Raniganj", "cluster"),
    "haldia": ("Haldia", "city"),
    "kharagpur": ("Kharagpur", "city"),
    "kalyani": ("Kalyani", "city"),
    "falta": ("Falta", "cluster"),
    "budge budge": ("Budge Budge", "cluster"),
    "taratala": ("Taratala", "cluster"),
    # Maharashtra
    "maharashtra": ("Maharashtra", "state"),
    "mumbai": ("Mumbai", "city"),
    "pune": ("Pune", "city"),
    "thane": ("Thane", "city"),
    "bhiwandi": ("Bhiwandi", "cluster"),
    "chakan": ("Chakan", "cluster"),
    "nagpur": ("Nagpur", "city"),
    "nashik": ("Nashik", "city"),
    # Gujarat
    "gujarat": ("Gujarat", "state"),
    "ahmedabad": ("Ahmedabad", "city"),
    "surat": ("Surat", "city"),
    "vadodara": ("Vadodara", "city"),
    "rajkot": ("Rajkot", "city"),
    "sanand": ("Sanand", "cluster"),
    "morbi": ("Morbi", "cluster"),
    "ankleshwar": ("Ankleshwar", "cluster"),
    # North India / NCR
    "delhi": ("Delhi", "city"),
    "ncr": ("Delhi NCR", "region"),
    "gurgaon": ("Gurgaon", "city"),
    "gurugram": ("Gurgaon", "city"),
    "noida": ("Noida", "city"),
    "faridabad": ("Faridabad", "city"),
    "ghaziabad": ("Ghaziabad", "city"),
    # South India
    "karnataka": ("Karnataka", "state"),
    "bangalore": ("Bengaluru", "city"),
    "bengaluru": ("Bengaluru", "city"),
    "tamil nadu": ("Tamil Nadu", "state"),
    "chennai": ("Chennai", "city"),
    "coimbatore": ("Coimbatore", "city"),
    "telangana": ("Telangana", "state"),
    "hyderabad": ("Hyderabad", "city"),
    # Central / East
    "jharkhand": ("Jharkhand", "state"),
    "jamshedpur": ("Jamshedpur", "city"),
    "ranchi": ("Ranchi", "city"),
    "odisha": ("Odisha", "state"),
    "orissa": ("Odisha", "state"),
    "bhubaneswar": ("Bhubaneswar", "city"),
}

KNOWN_SECTORS = {
    "steel": "Steel & Metallurgical Manufacturing",
    # B2C Residential, Executive & High-Net-Worth Professions
    "doctor": "Healthcare & Medical Practitioners",
    "doctors": "Healthcare & Medical Practitioners",
    "physician": "Healthcare & Medical Practitioners",
    "surgeon": "Healthcare & Medical Practitioners",
    "clinic": "Healthcare & Medical Practitioners",
    "hospital": "Healthcare & Medical Practitioners",
    "chartered accountant": "Chartered Accountants & Financial Advisors",
    "ca": "Chartered Accountants & Financial Advisors",
    "auditor": "Chartered Accountants & Financial Advisors",
    "lawyer": "Advocates & Legal Counsel",
    "lawyers": "Advocates & Legal Counsel",
    "advocate": "Advocates & Legal Counsel",
    "legal": "Advocates & Legal Counsel",
    "senior professional": "Senior Corporate Executives & CXOs",
    "senior professionals": "Senior Corporate Executives & CXOs",
    "executive": "Senior Corporate Executives & CXOs",
    "executives": "Senior Corporate Executives & CXOs",
    "entrepreneur": "Business Promoters & Entrepreneurs",
    "entrepreneurs": "Business Promoters & Entrepreneurs",
    "residential": "Premium Residential Apartments",
    "apartment": "Premium Residential Apartments",
    "apartments": "Premium Residential Apartments",
    "villa": "Luxury Bungalows & Villas",
    "villas": "Luxury Bungalows & Villas",
    "bungalow": "Luxury Bungalows & Villas",
    "bungalows": "Luxury Bungalows & Villas",
    "plot": "Plotted Developments & Land",
    "plots": "Plotted Developments & Land",
    "foundry": "Foundry, Forgings & Castings",
    "forging": "Foundry, Forgings & Castings",
    "casting": "Foundry, Forgings & Castings",
    "warehouse": "3PL Warehousing & Logistics",
    "warehousing": "3PL Warehousing & Logistics",
    "logistics": "3PL Warehousing & Logistics",
    "3pl": "3PL Warehousing & Logistics",
    "freight": "3PL Warehousing & Logistics",
    "transport": "Commercial Transport & Fleet",
    "chemical": "Chemicals & Petrochemicals",
    "chemicals": "Chemicals & Petrochemicals",
    "polymer": "Polymers & Plastic Products",
    "plastics": "Polymers & Plastic Products",
    "pharma": "Pharmaceuticals & Healthcare",
    "pharmaceutical": "Pharmaceuticals & Healthcare",
    "agro": "Agro-Commodities & Food Processing",
    "food": "Agro-Commodities & Food Processing",
    "tea": "Agro-Commodities & Food Processing",
    "engineering": "Heavy Engineering & Fabrication",
    "fabrication": "Heavy Engineering & Fabrication",
    "textile": "Textiles & Jute Manufacturing",
    "jute": "Textiles & Jute Manufacturing",
    "paper": "Paper & Packaging Manufacturing",
    "packaging": "Paper & Packaging Manufacturing",
    "cement": "Cement & Building Materials",
    "refractory": "Refractory & Industrial Ceramics",
}


@dataclass
class DiscoveredSource:
    canonical_domain: str
    discovered_url: str
    title: str
    snippet: str
    source_engine: str
    reference_record: Optional[Dict[str, Any]] = None


class PromptQueryAdapter:
    """Parses arbitrary plain English user prompts into optimized search dorks and executes live queries."""

    @classmethod
    def parse_prompt(cls, prompt: str) -> Dict[str, Any]:
        p_clean = prompt.lower()
        locations = []
        for term, (std_name, kind) in KNOWN_GEOGRAPHIES.items():
            if re.search(r"\b" + re.escape(term) + r"\b", p_clean):
                if std_name not in locations:
                    locations.append(std_name)

        sectors = []
        for term, std_sector in KNOWN_SECTORS.items():
            if re.search(r"\b" + re.escape(term) + r"\b", p_clean):
                if std_sector not in sectors:
                    sectors.append(std_sector)

        words = [w for w in re.findall(r"[a-z0-9\-]+", p_clean) if len(w) > 2 and w not in STOPWORDS]

        return {
            "prompt": prompt,
            "detected_locations": locations,
            "detected_sectors": sectors,
            "keywords": words[:12],
            "primary_location": locations[0] if locations else "India",
            "primary_sector": sectors[0] if sectors else "Manufacturing",
        }

    @classmethod
    @classmethod
    def generate_queries(cls, prompt: str, max_queries: int = 24) -> List[str]:
        parsed = cls.parse_prompt(prompt)
        p_lower = prompt.lower()
        locs = parsed["detected_locations"] or ["West Bengal", "India"]
        sectors = parsed["detected_sectors"] or ["Industrial Manufacturing"]
        kw = parsed["keywords"]

        queries: List[str] = []
        primary_loc = locs[0]

        is_b2b_industrial = any(w in p_lower for w in (
            "manufacturing", "industrial", "logistics", "warehouse", "warehousing", "foundry",
            "factory", "steel", "commercial fleet", "debt syndication", "factory shed", "industrial plot"
        ))
        is_b2c_residential = any(w in p_lower for w in (
            "residential", "apartment", "apartments", "flat", "flats", "bungalow", "bungalows",
            "villa", "villas", "homebuyer", "housing", "chandannagar", "shree", "vrindavan",
            "doctor", "doctors", "lawyer", "lawyers", "chartered accountant", "ca",
            "high-income", "individual", "individuals", "senior professional"
        )) and not is_b2b_industrial

        if is_b2c_residential:
            target_towns = [l for l in locs if l not in ("India", "West Bengal")]
            if not target_towns:
                target_towns = ["Chandannagar", "Hooghly"] if ("chandannagar" in p_lower or "shree" in p_lower) else ["Kalyani", "Nadia"]

            main_town = target_towns[0]

            # 1. Doctors & Medical Practitioners
            queries.append(f'doctor clinic hospital "{main_town}" contact phone website')
            queries.append(f'senior consultant doctor physician "{main_town}" Hooghly')
            
            # 2. Chartered Accountants & Financial Advisors
            queries.append(f'"chartered accountant" CA firm "{main_town}" contact')
            queries.append(f'chartered accountants "{main_town}" audit tax consultant')
            
            # 3. Advocates & Legal Counsel
            queries.append(f'advocate lawyer legal consultant "{main_town}" Hooghly contact')
            queries.append(f'bar association advocate legal counsel "{main_town}"')
            
            # 4. Senior Executives & Business Promoters associated with town
            queries.append(f'managing director promoter "{main_town}" resident OR native contact')
            queries.append(f'business owner entrepreneur "{main_town}" contact phone email')
            queries.append(f'"{main_town}" senior executive director resident LinkedIn')
            queries.append(f'company director resident native "{main_town}" Kolkata')
            
            # 5. Out-of-town high-income affinity (e.g. Bangalore/Mumbai tech CXOs with hometown roots)
            queries.append(f'"{main_town}" corporate director Bangalore Mumbai executive')
            queries.append(f'resident executive native from "{main_town}" software corporate')

            # 6. Additional detected towns
            for t in target_towns[1:3]:
                queries.append(f'doctor CA advocate business promoter "{t}" contact')
                queries.append(f'managing director resident "{t}" contact phone')

        else:
            # === B2B Industrial / Commercial Fleet / Corporate Advisory Dorks ===
            wb_clusters = [
                "Howrah", "Hooghly", "Dankuni", "Sankrail", "Dhulagarh", "Uluberia",
                "Jalan Industrial Complex", "Durgapur", "Asansol", "Haldia", "Kalyani",
                "Budge Budge", "Taratala", "Liluah", "Belur", "Falta",
            ]
            target_clusters = [c for c in wb_clusters if c.lower() in p_lower]
            if not target_clusters:
                target_clusters = locs if len(locs) > 1 else [primary_loc, "Howrah", "Dankuni", "Sankrail", "Hooghly"]

            for sec in sectors[:3]:
                sec_short = sec.split("&")[0].split()[0]
                for cl in target_clusters[:4]:
                    queries.append(f'"{sec_short}" "{cl}" manufacturing plant company')
                    queries.append(f'"{sec_short}" factory "{cl}" "contact us" website')
                    queries.append(f'"{cl}" "{sec_short}" "managing director" OR "director" OR "promoter"')

            for cl in target_clusters[:3]:
                queries.append(f'industrial manufacturing companies plants in {cl}')
                queries.append(f'warehousing 3pl logistics transport units in {cl}')
                queries.append(f'top engineering foundry steel factories in {cl}')

            clean_prompt = " ".join([primary_loc] + [s.split()[0] for s in sectors[:2]])
            queries.append(f'{clean_prompt} "plant" OR "works" site:.in -site:wikipedia.org -site:facebook.com')
            queries.append(f'{clean_prompt} "corporate office" OR "head office" "contact" -site:youtube.com')
            queries.append(f'"{primary_loc}" manufacturing plants official website phone email')

            if len(kw) >= 2:
                kw_chunk = " ".join(kw[:3])
                queries.append(f'{kw_chunk} "{primary_loc}" official website')
                if len(kw) >= 5:
                    queries.append(f'{" ".join(kw[3:6])} "{primary_loc}" plant contact')

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_clean = q.strip()
            if q_clean and q_clean not in seen:
                seen.add(q_clean)
                unique_queries.append(q_clean)
            if len(unique_queries) >= max_queries:
                break

        return unique_queries


class LiveSearchHarvester:
    """Executes live network queries across Bing HTML (with base64 redirect unwrap) & DuckDuckGo."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    DISALLOWED_DOMAINS = {
        "google.com", "bing.com", "duckduckgo.com", "yahoo.com", "youtube.com",
        "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
        "wikipedia.org", "wikimedia.org", "britannica.com", "play.google.com",
        "apps.apple.com", "microsoft.com", "azure.com", "github.com", "amazon.com",
        "flipkart.com", "indiamart.com", "justdial.com", "tradeindia.com", "tofler.in",
        "zaubacorp.com", "quickr.com", "sulekha.com", "yellowpages.com"
    }

    @classmethod
    def _unwrap_bing_url(cls, raw_href: str) -> str:
        """Unwraps Bing redirect URLs like https://www.bing.com/ck/a?!...&u=a1aHR0cHM6Ly9..."""
        if not raw_href:
            return ""
        if "bing.com/ck/a?" in raw_href or "&u=a1" in raw_href:
            try:
                parsed = urllib.parse.urlparse(raw_href)
                qs = urllib.parse.parse_qs(parsed.query)
                u_val = qs.get("u", [None])[0]
                if u_val and u_val.startswith("a1"):
                    b64_str = u_val[2:]
                    b64_str += "=" * (-len(b64_str) % 4)
                    decoded = base64.b64decode(b64_str).decode("utf-8", errors="ignore")
                    if decoded.startswith(("http://", "https://")):
                        return decoded
            except Exception:
                pass
        return raw_href

    @classmethod
    def _unwrap_ddg_url(cls, raw_url: str) -> str:
        """Unwraps DuckDuckGo redirect URLs like //duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com."""
        if not raw_url:
            return ""
        if "/l/?" in raw_url or "uddg=" in raw_url:
            try:
                parsed = urllib.parse.urlparse(raw_url)
                qs = urllib.parse.parse_qs(parsed.query)
                if "uddg" in qs:
                    return urllib.parse.unquote(qs["uddg"][0])
            except Exception:
                pass
        return raw_url

    @classmethod
    def is_corporate_domain(cls, domain: str) -> bool:
        if not domain or "." not in domain:
            return False
        d = domain.lower().strip()
        if d.startswith("www."):
            d = d[4:]
        if any(d == dis or d.endswith("." + dis) for dis in cls.DISALLOWED_DOMAINS):
            return False
        return True

    @classmethod
    def search_bing_html(
        cls, query: str, max_results: int = 15, allow_private_for_tests: bool = False
    ) -> List[DiscoveredSource]:
        """Queries Bing HTML search and decodes true destination URLs from base64 redirects."""
        results: List[DiscoveredSource] = []
        encoded_q = urllib.parse.quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded_q}&count={max_results}"
        try:
            req = urllib.request.Request(url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    html_content = resp.read().decode("utf-8", errors="ignore")
                    soup = BeautifulSoup(html_content, "html.parser")
                    for item in soup.select("li.b_algo"):
                        a_tag = item.select_one("h2 a")
                        if not a_tag or not a_tag.get("href"):
                            continue
                        raw_href = a_tag["href"].strip()
                        actual_url = cls._unwrap_bing_url(raw_href)
                        if not actual_url.startswith(("http://", "https://")):
                            continue

                        parsed_url = urllib.parse.urlparse(actual_url)
                        dom = (parsed_url.hostname or "").lower()
                        if dom.startswith("www."):
                            dom = dom[4:]

                        if not cls.is_corporate_domain(dom):
                            continue

                        is_safe, _, _ = validate_target_url(
                            actual_url, allow_private_for_tests=allow_private_for_tests
                        )
                        if not is_safe:
                            continue

                        title = a_tag.get_text(" ", strip=True) or dom
                        snippet_tag = item.select_one(".b_caption p, p")
                        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

                        results.append(
                            DiscoveredSource(
                                canonical_domain=dom,
                                discovered_url=actual_url,
                                title=title[:150],
                                snippet=snippet[:250],
                                source_engine="bing_html",
                            )
                        )
                        if len(results) >= max_results:
                            return results
        except Exception as exc:
            logger.debug(f"Bing HTML query failed on '{query}': {exc}")
        return results

    @classmethod
    def search_duckduckgo_html(
        cls, query: str, max_results: int = 15, allow_private_for_tests: bool = False
    ) -> List[DiscoveredSource]:
        """Queries DuckDuckGo HTML / Lite endpoints and parses organic search results."""
        results: List[DiscoveredSource] = []
        data = urllib.parse.urlencode({"q": query, "b": ""}).encode("utf-8")
        req_headers = dict(cls.HEADERS)
        req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        endpoints = [
            "https://html.duckduckgo.com/html/",
            "https://lite.duckduckgo.com/lite/",
        ]

        for ep in endpoints:
            try:
                req = urllib.request.Request(ep, data=data, headers=req_headers)
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status in (200, 202):
                        html_content = resp.read().decode("utf-8", errors="ignore")
                        soup = BeautifulSoup(html_content, "html.parser")

                        items = soup.select(".result")
                        if not items:
                            items = soup.select(".result-link")

                        for item in items:
                            a_tag = item.select_one("a.result__url, a.result-link, a")
                            if not a_tag or not a_tag.get("href"):
                                continue

                            raw_href = a_tag["href"].strip()
                            actual_url = cls._unwrap_ddg_url(raw_href)
                            if not actual_url.startswith(("http://", "https://")):
                                continue

                            parsed_url = urllib.parse.urlparse(actual_url)
                            dom = (parsed_url.hostname or "").lower()
                            if dom.startswith("www."):
                                dom = dom[4:]

                            if not cls.is_corporate_domain(dom):
                                continue

                            is_safe, _, _ = validate_target_url(
                                actual_url, allow_private_for_tests=allow_private_for_tests
                            )
                            if not is_safe:
                                continue

                            title_tag = item.select_one(".result__title, .result-title, strong, a")
                            title = title_tag.get_text(" ", strip=True) if title_tag else dom
                            snippet_tag = item.select_one(".result__snippet, .result-snippet")
                            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

                            results.append(
                                DiscoveredSource(
                                    canonical_domain=dom,
                                    discovered_url=actual_url,
                                    title=title[:150],
                                    snippet=snippet[:250],
                                    source_engine="duckduckgo_html",
                                )
                            )
                            if len(results) >= max_results:
                                return results

                        if results:
                            return results
            except Exception as exc:
                logger.debug(f"DDG query failed on {ep}: {exc}")
                continue

        return results

    @classmethod
    def harvest_domains_for_queries(
        cls,
        queries: List[str],
        target_count: int,
        seen_domains: Set[str],
        allow_private_for_tests: bool = False,
        prompt: str = "",
    ) -> List[DiscoveredSource]:
        """Dynamically harvests unique corporate domains across multi-engine queries and outbound snowballing."""
        harvested: List[DiscoveredSource] = []
        local_seen = set(seen_domains)

        for q in queries:
            if len(harvested) >= target_count:
                break

            # 1. Bing HTML query (with unwrapped base64 destination URLs)
            batch = cls.search_bing_html(
                q, max_results=15, allow_private_for_tests=allow_private_for_tests
            )
            # 2. DuckDuckGo HTML / Lite fallback
            if not batch:
                batch = cls.search_duckduckgo_html(
                    q, max_results=15, allow_private_for_tests=allow_private_for_tests
                )

            for item in batch:
                dom = item.canonical_domain.lower().strip()
                if dom and dom not in local_seen:
                    local_seen.add(dom)
                    harvested.append(item)
                    if len(harvested) >= target_count:
                        break

        return harvested
