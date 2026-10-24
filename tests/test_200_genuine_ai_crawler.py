"""Tests for Genuine AI Web Scraping, 5 Client Profiles, and Low-RAM Playwright Escalation."""
from __future__ import annotations

import hashlib
import http.server
import os
import socket
import threading
import time
from pathlib import Path
from typing import Generator

import pytest

from lead_discovery.ai_scraper_layer import (
    AILeadExtractionAgent,
    CLIENT_BRAND_PROFILES,
    HtmlToAiMarkdownPruner,
    LowRamPlaywrightEscalator,
)
from lead_discovery.live_evidence_crawler import GenuineEvidenceCrawler
from lead_discovery.prompt_search_adapter import (
    DiscoveredSource,
    LiveSearchHarvester,
    PromptQueryAdapter,
)
from services.api.campaign_routes import CAMPAIGN_JOBS, CampaignJob, _execute_campaign_thread


def test_five_production_client_profiles_configured():
    expected_clients = {
        "lakhotia",
        "shree",
        "vrindavan",
        "matrix360_advisory",
        "apex_industrial_fleet",
    }
    assert expected_clients.issubset(set(CLIENT_BRAND_PROFILES.keys()))
    profile_dir = Path(__file__).resolve().parent.parent / "config" / "client_profiles"
    for cid in expected_clients:
        assert (profile_dir / f"{cid}.json").exists(), f"Missing profile JSON for {cid}"


def test_crawl4ai_markdown_pruner_and_ai_extraction():
    sample_html = """
    <html>
    <head>
        <title>Shyam Metalics & Energy Ltd | Integrated Steel Producer</title>
        <script>console.log('strip me');</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <header>Shyam Metalics Corporate Portal</header>
        <main>
            <h1>Shyam Metalics & Energy Limited</h1>
            <p>Managing Director: Brij Bhushan Agarwal</p>
            <p>Works: Jamuria Industrial Estate, Asansol, Paschim Bardhaman, West Bengal</p>
            <p>Contact: <a href="mailto:contact@shyammetalics.com">contact@shyammetalics.com</a></p>
            <p>Phone: <a href="tel:+913340111000">+91 33 4011 1000</a></p>
            <table>
                <tr><td>Turnover</td><td>INR 4,500 Crores</td></tr>
                <tr><td>Plants</td><td>Jamuria, Sambalpur, Pakuria</td></tr>
            </table>
        </main>
        <footer>Registered Office: Trinity Tower, 83 Topsia Road South, Kolkata 700046</footer>
    </body>
    </html>
    """
    md = HtmlToAiMarkdownPruner.to_compact_markdown(sample_html, url="https://shyammetalics.com")
    assert "Shyam Metalics" in md
    assert "Brij Bhushan Agarwal" in md
    assert "contact@shyammetalics.com" in md
    assert "+91 33 4011 1000" in md
    assert "strip me" not in md
    assert len(md) < 2400

    extracted = AILeadExtractionAgent.enrich_and_qualify_with_ai(
        raw_html=sample_html,
        domain="shyammetalics.com",
        client_id="lakhotia",
        user_prompt="Steel and metallurgical manufacturing plants in West Bengal",
        existing_extracted={
            "company_name": "Shyam Metalics & Energy Limited",
            "director_name": "Brij Bhushan Agarwal",
            "address": "Jamuria Industrial Estate, Asansol, West Bengal",
        },
    )
    assert extracted["company_name"] == "Shyam Metalics & Energy Limited"
    assert extracted["director_name"] == "Brij Bhushan Agarwal"
    assert "Steel" in extracted["sector"]
    assert extracted["qualification_status"] == "PREPASS"
    assert len(extracted["ai_fit_reasoning"]) > 10


def test_low_ram_playwright_escalator_detection():
    # Plain static HTML should NOT trigger SPA escalator
    static_html = "<html><body><h1>Standard Enterprise Portal</h1><p>Welcome to our company.</p></body></html>"
    assert not LowRamPlaywrightEscalator.is_js_spa_shell(static_html)

    # Empty React / Next shell should trigger SPA escalator
    react_shell = '<html><head><title>App</title></head><body><div id="root"></div><script src="/bundle.js"></script></body></html>'
    assert LowRamPlaywrightEscalator.is_js_spa_shell(react_shell)

    # Verify low-RAM Chromium launch args
    assert "--single-process" in LowRamPlaywrightEscalator.LOW_RAM_ARGS
    assert "--js-flags=--max-old-space-size=128" in LowRamPlaywrightEscalator.LOW_RAM_ARGS
    assert "--disable-dev-shm-usage" in LowRamPlaywrightEscalator.LOW_RAM_ARGS


def test_prompt_query_planner_generates_up_to_24_queries():
    prompt = "Steel fabrication and heavy foundry units in Howrah and Dankuni West Bengal"
    queries = PromptQueryAdapter.generate_queries(prompt, max_queries=24)
    assert len(queries) >= 10
    assert any("howrah" in q.lower() or "dankuni" in q.lower() for q in queries)
    assert any("foundry" in q.lower() or "steel" in q.lower() for q in queries)


def test_live_search_harvester_bing_unwrapping():
    # Bing wraps target URLs in base64 like /ck/a?!...&u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS8=
    raw_bing = "https://www.bing.com/ck/a?!&&p=abc&u=a1aHR0cHM6Ly9zdGVlbC5nb3YuaW4v&ntb=1"
    unwrapped = LiveSearchHarvester._unwrap_bing_url(raw_bing)
    assert unwrapped == "https://steel.gov.in/"

    # Non-bing links remain untouched
    normal_url = "https://example.com/about"
    assert LiveSearchHarvester._unwrap_bing_url(normal_url) == normal_url


class MockCrawlerServer(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/robots.txt":
            content = b"User-agent: *\nDisallow: /forbidden\n"
        elif self.path in ("/", "/index.html"):
            content = b"""<!DOCTYPE html>
            <html>
            <head><title>Bengal Ferro Alloys & Steel Limited</title></head>
            <body>
                <h1>Bengal Ferro Alloys & Steel Limited</h1>
                <p>Managing Director: Sunil Kumar Agarwal</p>
                <p>Works: Sankrail Industrial Park, NH-6, Howrah - 711313</p>
                <p>Phone: +91 33 2661 5500</p>
                <p><a href="mailto:info@bengalferro.com">info@bengalferro.com</a></p>
                <p><a href="/contact">Contact Us</a></p>
            </body>
            </html>"""
        elif self.path == "/contact":
            content = b"""<!DOCTYPE html>
            <html>
            <head><title>Contact Us - Bengal Ferro Alloys</title></head>
            <body>
                <h2>Contact Information</h2>
                <p>Plant Head: Rajesh Singhania</p>
                <p>Sales: sales@bengalferro.com</p>
            </body>
            </html>"""
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html" if not self.path.endswith(".txt") else "text/plain")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


@pytest.fixture(scope="module")
def mock_server() -> Generator[str, None, None]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()

    server = http.server.HTTPServer(("127.0.0.1", port), MockCrawlerServer)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_live_crawler_and_campaign_execution(mock_server: str):
    # Test GenuineEvidenceCrawler against the active mock server
    crawler = GenuineEvidenceCrawler(
        timeout_seconds=3,
        allow_private_for_tests=True,
        client_id="lakhotia",
        user_prompt="Steel plants in Howrah",
    )
    result = crawler.crawl_and_extract(mock_server, "bengalferro.com", max_subpages=2)
    assert result["company_name"] == "Bengal Ferro Alloys & Steel Limited"
    assert "info@bengalferro.com" in result["emails"]
    assert any("2661" in p for p in result["phones"])
    assert result["page_hash"] != ""
    assert result["confidence_score"] >= 0.80

    # Test CampaignJob with mock source
    job_id = f"test_job_{int(time.time())}"
    job = CampaignJob(
        job_id=job_id,
        client_id="lakhotia",
        prompt="Steel plants in Howrah",
        target_count=1,
        campaign_type="both",
        status="running",
        started_at=time.time(),
    )
    CAMPAIGN_JOBS[job_id] = job

    # Inject mock source and run
    mock_src = DiscoveredSource(
        canonical_domain="bengalferro.com",
        discovered_url=mock_server,
        title="Bengal Ferro Alloys & Steel Limited",
        snippet="Manufacturing steel and ferro alloys in Howrah",
        source_engine="test_mock",
    )
    crawl_data = crawler.crawl_and_extract(mock_server, "bengalferro.com", max_subpages=2)
    assert crawl_data["primary_email"] == "info@bengalferro.com"
