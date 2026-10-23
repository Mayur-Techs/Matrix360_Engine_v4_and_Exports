"""End-to-End Live Crawling & Evidence Verification Test.

Proves a genuine network HTTP fetch against an active live web server,
demonstrates Cloudflare XOR decoding, robots.txt blocking, Schema.org parsing,
and verifies persisted evidence in SQLite ProductionLeadVault.
"""
from __future__ import annotations

import http.server
import os
import socket
import tempfile
import threading
from pathlib import Path
from typing import Generator

import pytest

from engine_v5.unified_pipeline import ProductionLeadVault
from lead_discovery.live_evidence_crawler import GenuineEvidenceCrawler
from lead_discovery.security_guard import DomainRateLimiter, RobotsTxtGuard


class MockCorporateWebHandler(http.server.BaseHTTPRequestHandler):
    """Serves real HTML pages, Cloudflare obfuscation, robots.txt, and contact links."""

    def log_message(self, format, *args):
        # Suppress standard logging during tests
        pass

    def do_GET(self):
        if self.path == "/robots.txt":
            content = b"User-agent: *\nDisallow: /admin\nDisallow: /private\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path == "/private":
            content = b"<html><body>Secret internal data</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path in ("/", "/index.html"):
            # Homepage with Schema.org JSON-LD and internal navigation links
            html = """<!DOCTYPE html>
            <html>
            <head>
                <title>Eastern Steel & Heavy Forgings Limited | Official Portal</title>
                <meta property="og:site_name" content="Eastern Steel & Heavy Forgings Limited" />
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Corporation",
                    "name": "Eastern Steel & Heavy Forgings Limited",
                    "address": {
                        "@type": "PostalAddress",
                        "streetAddress": "Plot 14, Sankrail Industrial Park, NH-6",
                        "addressLocality": "Howrah",
                        "postalCode": "711302"
                    }
                }
                </script>
            </head>
            <body>
                <h1>Eastern Steel & Heavy Forgings Limited</h1>
                <p>Welcome to our industrial manufacturing facility.</p>
                <nav>
                    <a href="/contact">Contact & Plant Location</a>
                    <a href="/about">About Management</a>
                    <a href="/private">Internal Admin</a>
                </nav>
            </body>
            </html>"""
            b = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        if self.path == "/contact":
            # Contact page with mailto, tel, Cloudflare XOR email, and GSTIN
            # Cloudflare XOR hex for 'sales@easternsteel.co.in':
            # key = 0x5b
            # 's' ^ 0x5b = 0x38, 'a' ^ 0x5b = 0x3a, 'l' ^ 0x5b = 0x37, 'e' ^ 0x5b = 0x3e, 's' ^ 0x5b = 0x38,
            # '@' ^ 0x5b = 0x1b, 'e' ^ 0x5b = 0x3e, 'a' ^ 0x5b = 0x3a, 's' ^ 0x5b = 0x38, 't' ^ 0x5b = 0x3f,
            # 'e' ^ 0x5b = 0x3e, 'r' ^ 0x5b = 0x29, 'n' ^ 0x5b = 0x35, 's' ^ 0x5b = 0x38, 't' ^ 0x5b = 0x3f,
            # 'e' ^ 0x5b = 0x3e, 'e' ^ 0x5b = 0x3e, 'l' ^ 0x5b = 0x37, '.' ^ 0x5b = 0x75, 'c' ^ 0x5b = 0x38,
            # 'o' ^ 0x5b = 0x34, '.' ^ 0x5b = 0x75, 'i' ^ 0x5b = 0x32, 'n' ^ 0x5b = 0x35
            cf_hex = "255644494056654044565140574b56514040490b464a0b4c4b"
            html = f"""<!DOCTYPE html>
            <html>
            <head><title>Contact Us - Eastern Steel & Heavy Forgings</title></head>
            <body>
                <h2>Contact Information</h2>
                <p>Factory Works: Sankrail Industrial Park, NH-6, Howrah - 711302, West Bengal</p>
                <p>Corporate Mail: <a href="mailto:info@easternsteel.co.in">info@easternsteel.co.in</a></p>
                <p>Obfuscated Sales Desk: <a href="/cdn-cgi/l/email-protection#{cf_hex}" data-cfemail="{cf_hex}">[email protected]</a></p>
                <p>Works Board Phone: <a href="tel:+913326618327">+91 33 2661 8327</a></p>
                <p>GSTIN: 19AABCE1234F1Z9</p>
                <p>CIN: L27100WB1998PLC087654</p>
            </body>
            </html>"""
            b = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        if self.path == "/about":
            html = """<!DOCTYPE html>
            <html>
            <head><title>About Us - Leadership</title></head>
            <body>
                <h2>Board of Directors</h2>
                <p>Managing Director: Rajesh Goenka</p>
                <p>Executive Director: Amit Goenka</p>
            </body>
            </html>"""
            b = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return

        self.send_response(404)
        self.end_headers()


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def mock_server() -> Generator[str, None, None]:
    port = _get_free_port()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), MockCorporateWebHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.shutdown()
    server.server_close()


def test_end_to_end_crawler_live_fetch(mock_server: str, tmp_path: Path):
    """Proves genuine HTTP web fetching, contact parsing, robots checks, and vault persistence."""
    domain = "easternsteel.co.in"
    start_url = f"{mock_server}/"

    # Allow 127.0.0.1 target for local test fixture
    crawler = GenuineEvidenceCrawler(
        rate_limiter=DomainRateLimiter(min_delay_seconds=0.01),
        robots_guard=RobotsTxtGuard(user_agent="Matrix360Bot"),
        timeout_seconds=5,
        allow_private_for_tests=True,
    )

    # 1. Execute live multi-page crawl against the running HTTP server
    result = crawler.crawl_and_extract(start_url, domain, max_subpages=4)

    # 2. Verify genuine crawl facts
    assert result["canonical_domain"] == domain
    assert result["company_name"] == "Eastern Steel & Heavy Forgings Limited"
    assert result["pages_crawled_count"] >= 3  # homepage + /contact + /about

    # 3. Verify extracted contacts
    # Plain text mailto
    assert "info@easternsteel.co.in" in result["emails"]
    # Cloudflare XOR decoded email
    assert "sales@easternsteel.co.in" in result["emails"]
    # Telephone number
    assert any("26618327" in p for p in result["phones"])

    # 4. Verify leadership & regulatory evidence
    assert result["director_name"] in ("Rajesh Goenka", "Amit Goenka")
    assert "Rajesh Goenka" in result["all_directors"]
    assert "Amit Goenka" in result["all_directors"]
    assert "19AABCE1234F1Z9" in result["gstins"]
    assert "L27100WB1998PLC087654" in result["cins"]

    # 5. Verify page hash and verified source URL
    assert result["page_hash"] != ""
    assert len(result["page_hash"]) == 64  # SHA256 length
    assert result["verified_source_url"].startswith("http://127.0.0.1")

    # 6. Verify robots.txt disallowed path was NOT crawled
    for page in result["visited_pages"]:
        assert "/private" not in page["url"]

    # 7. Verify ZERO fabrication: turnover was not on the website, so it must be None!
    assert result["turnover"] is None

    # 8. Verify persistence to SQLite ProductionLeadVault with provenance
    test_db = tmp_path / "test_production_vault.db"
    vault = ProductionLeadVault(test_db)

    lead_record = {
        "lead_id": f"lakhotia:{domain}",
        "company_name": result["company_name"],
        "canonical_domain": domain,
        "director_name": result["director_name"],
        "phone": result["primary_phone"],
        "email": result["primary_email"],
        "catchment_district": "Howrah",
        "verified_source_url": result["verified_source_url"],
        "page_hash": result["page_hash"],
        "qualification_status": "PREPASS",
        "confidence_score": result["confidence_score"],
    }
    saved = vault.upsert_leads([lead_record], client_id="lakhotia")
    assert saved == 1

    # Read back from DB and verify exact provenance retention
    persisted = vault.list_leads(client_id="lakhotia")
    assert len(persisted) == 1
    row = persisted[0]
    assert row["company_name"] == "Eastern Steel & Heavy Forgings Limited"
    assert row["canonical_domain"] == domain
    assert row["verified_source_url"] == result["verified_source_url"]
    assert row["named_contact"] in ("Rajesh Goenka", "Amit Goenka")
    assert row["company_email"] == "info@easternsteel.co.in"
