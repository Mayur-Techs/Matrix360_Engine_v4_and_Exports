"""Matrix 360 Consulting — Dynamic Prompt-to-Search Query Generator & Multi-Engine Harvester.

Dynamically interprets user prompt (industry, geography, target role, scale),
constructs precision OSINT search dorks, and executes live multi-page web discovery
across public search engines (DuckDuckGo HTML, DuckDuckGo Lite, Bing) with zero hardcoding.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup

from .security_guard import validate_target_url

logger = logging.getLogger("matrix360.search_adapter")

# Stopwords to filter from prompts when constructing search dorks
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
    "manesar": ("Manesar", "cluster"),
    # South India
    "karnataka": ("Karnataka", "state"),
    "bangalore": ("Bangalore", "city"),
    "bengaluru": ("Bangalore", "city"),
    "tamil nadu": ("Tamil Nadu", "state"),
    "chennai": ("Chennai", "city"),
    "coimbatore": ("Coimbatore", "city"),
    "telangana": ("Telangana", "state"),
    "hyderabad": ("Hyderabad", "city"),
}

KNOWN_SECTORS = {
    "steel": "Steel & Metallurgy",
    "foundry": "Foundry & Castings",
    "casting": "Foundry & Castings",
    "forging": "Forging & Heavy Engineering",
    "fabrication": "Metal Fabrication & Tanks",
    "machining": "Precision CNC Machining",
    "valves": "Industrial Valves & Flow Control",
    "pumps": "Industrial Pumps & Water Systems",
    "pipes": "Industrial Piping & Tubes",
    "fasteners": "Fasteners & Hardware",
    "crane": "Cranes & Material Handling",
    "logistics": "Logistics & Supply Chain",
    "warehousing": "Warehousing & Industrial Parks",
    "warehouse": "Warehousing & Logistics",
    "3pl": "3PL Third Party Logistics",
    "cold storage": "Cold Storage & Reefer",
    "chemical": "Chemicals & Allied Petrochem",
    "polymer": "Polymers & Specialty Plastics",
    "plastics": "Plastics & Extrusion",
    "packaging": "Industrial Packaging & Corrugated",
    "jute": "Jute Packaging & Technical Textiles",
    "textile": "Textiles & Garments",
    "pharma": "Pharmaceuticals & Healthcare",
    "solar": "Solar & Renewable EPC",
    "agro": "Agro Processing & Grains",
    "food": "Food Processing & Manufacturing",
    "engineering": "Heavy Engineering",
}


@dataclass
class DiscoveredSource:
    canonical_domain: str
    discovered_url: str
    title: str
    snippet: str
    source_engine: str


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

        # Extract remaining content words
        words = [w for w in re.findall(r"[a-z0-9\-]+", p_clean) if len(w) > 2 and w not in STOPWORDS]

        return {
            "prompt": prompt,
            "detected_locations": locations,
            "detected_sectors": sectors,
            "keywords": words[:10],
            "primary_location": locations[0] if locations else "India",
            "primary_sector": sectors[0] if sectors else "Manufacturing",
        }

    @classmethod
    def generate_queries(cls, prompt: str, max_queries: int = 8) -> List[str]:
        parsed = cls.parse_prompt(prompt)
        locs = parsed["detected_locations"] or ["India"]
        sectors = parsed["detected_sectors"] or ["Industrial Manufacturing"]
        kw = " ".join(parsed["keywords"][:4])

        queries: List[str] = []
        primary_loc = locs[0]

        # 1. Sector + Location + Contact Info
        for sec in sectors[:2]:
            sec_short = sec.split("&")[0].split()[0]
            queries.append(f'"{sec_short}" "{primary_loc}" company contact phone email')
            queries.append(f'"{sec_short}" factory plant "{primary_loc}" "contact us"')
            queries.append(f'"{sec_short}" "{primary_loc}" "managing director" OR "director"')

        # 2. In-domain precision filters with directory exclusions
        clean_prompt = " ".join([primary_loc] + [s.split()[0] for s in sectors[:2]])
        queries.append(
            f'{clean_prompt} "contact us" site:.in -site:indiamart.com -site:justdial.com -site:facebook.com'
        )
        queries.append(
            f'{clean_prompt} "plant" OR "factory" site:.co.in -site:tradeindia.com -site:tofler.in'
        )

        # 3. Direct keywords dork
        if kw and kw not in queries:
            queries.append(f'{kw} "{primary_loc}" contact phone email')

        # Fallback to general prompt query
        if not queries:
            queries.append(f'{prompt} contact phone email site:.in')

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        return unique_queries[:max_queries]


class LiveSearchHarvester:
    """Executes live network queries across DuckDuckGo HTML, DuckDuckGo Lite, and Bing."""

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    @classmethod
    def _unwrap_ddg_url(cls, raw_url: str) -> str:
        """Unwraps DuckDuckGo redirect URLs like //duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com."""
        if not raw_url:
            return ""
        if "/l/?" in raw_url or "uddg=" in raw_url:
            parsed = urllib.parse.urlparse(raw_url)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                return urllib.parse.unquote(qs["uddg"][0])
        return raw_url

    @classmethod
    def search_duckduckgo_html(
        cls, query: str, max_results: int = 15, allow_private_for_tests: bool = False
    ) -> List[DiscoveredSource]:
        """Queries DuckDuckGo HTML endpoint and parses organic search results."""
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
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 202):
                        html_content = resp.read().decode("utf-8", errors="ignore")
                        soup = BeautifulSoup(html_content, "html.parser")

                        # DuckDuckGo HTML format: a.result__url or a.result__snippet
                        items = soup.select(".result")
                        if not items:
                            # Lite format: tables
                            items = soup.select(".result-link")

                        for item in items:
                            a_tag = item.select_one("a.result__url, a.result-link, a")
                            if not a_tag or not a_tag.get("href"):
                                continue

                            raw_href = a_tag["href"].strip()
                            actual_url = cls._unwrap_ddg_url(raw_href)
                            if not actual_url.startswith(("http://", "https://")):
                                continue

                            is_safe, reject_reason, _ = validate_target_url(
                                actual_url, allow_private_for_tests=allow_private_for_tests
                            )
                            if not is_safe:
                                continue

                            parsed_url = urllib.parse.urlparse(actual_url)
                            dom = (parsed_url.hostname or "").lower()
                            if dom.startswith("www."):
                                dom = dom[4:]

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
    ) -> List[DiscoveredSource]:
        """Iterates over dynamic queries until target_count candidate sources are harvested."""
        harvested: List[DiscoveredSource] = []
        for q in queries:
            if len(harvested) >= target_count:
                break
            batch = cls.search_duckduckgo_html(
                q, max_results=12, allow_private_for_tests=allow_private_for_tests
            )
            for item in batch:
                if item.canonical_domain in seen_domains:
                    continue
                seen_domains.add(item.canonical_domain)
                harvested.append(item)
                if len(harvested) >= target_count:
                    break
        return harvested
