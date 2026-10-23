"""Tests for Matrix 360 Consulting genuine evidence-bound live web crawler and exports."""
import hashlib
import time
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.campaign_routes import (
    _clean_phone,
    CAMPAIGN_JOBS,
    CampaignJob,
)
from lead_discovery.security_guard import (
    validate_target_url,
    RobotsTxtGuard,
    is_ip_private_or_restricted,
)
from lead_discovery.prompt_search_adapter import (
    PromptQueryAdapter,
)
from lead_discovery.live_evidence_crawler import GenuineEvidenceCrawler


def test_clean_phone_formatting():
    assert _clean_phone("9831118255") == "+919831118255"
    assert _clean_phone("+919007211599") == "+919007211599"
    assert _clean_phone("09831118255") == "+919831118255"
    assert _clean_phone("919831118255") == "+919831118255"
    assert _clean_phone(None) is None
    assert _clean_phone("123") is None  # Too short


def test_prompt_query_adapter_dynamic_generation():
    # West Bengal prompt
    wb_queries = PromptQueryAdapter.generate_queries(
        "Cast iron foundry and steel plant manufacturers in Howrah and Dankuni",
        max_queries=4,
    )
    assert len(wb_queries) >= 2
    assert any("Howrah" in q or "Dankuni" in q for q in wb_queries)
    assert any("foundry" in q.lower() or "steel" in q.lower() for q in wb_queries)

    # Gujarat solar prompt — must NOT generate hardcoded West Bengal queries!
    guj_queries = PromptQueryAdapter.generate_queries(
        "Solar panel manufacturers and EPC contractors in Ahmedabad Gujarat",
        max_queries=4,
    )
    assert len(guj_queries) >= 2
    assert any("Gujarat" in q or "Ahmedabad" in q for q in guj_queries)
    assert not any("Howrah" in q or "Kolkata" in q for q in guj_queries)

    # Maharashtra logistics prompt
    pune_queries = PromptQueryAdapter.generate_queries(
        "3PL warehousing and logistics fleet owners in Pune Maharashtra",
        max_queries=4,
    )
    assert any("Pune" in q or "Maharashtra" in q for q in pune_queries)
    assert not any("Howrah" in q for q in pune_queries)


def test_dns_aware_ssrf_guard():
    # Loopback IP targets must be blocked
    safe, reason, _ = validate_target_url("http://127.0.0.1:8000/admin")
    assert not safe
    assert "SSRF" in reason or "RAW_IP" in reason

    # Private RFC1918 targets must be blocked
    safe, reason, _ = validate_target_url("http://192.168.1.10/contact")
    assert not safe
    assert "SSRF" in reason or "RAW_IP" in reason

    # AWS / Cloud metadata link-local target must be blocked
    safe, reason, _ = validate_target_url("http://169.254.169.254/latest/meta-data/")
    assert not safe

    # Directory and social portals must be excluded
    safe, reason, _ = validate_target_url("https://www.indiamart.com/company")
    assert not safe
    assert "THIRD_PARTY_DIRECTORY" in reason

    safe, reason, _ = validate_target_url("https://facebook.com/page")
    assert not safe

    # Test private check helper
    assert is_ip_private_or_restricted("10.0.0.5") is True
    assert is_ip_private_or_restricted("127.0.0.1") is True
    assert is_ip_private_or_restricted("169.254.169.254") is True
    assert is_ip_private_or_restricted("8.8.8.8") is False


def test_robots_guard_disallow():
    guard = RobotsTxtGuard()
    # When allow_private_for_tests is true, returns True
    assert guard.can_fetch("http://test.local/contact", allow_private_for_tests=True) is True


def test_evidence_crawler_extraction_and_provenance(monkeypatch):
    """Test GenuineEvidenceCrawler on mock HTML with verified facts and provenance."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Apex Forgings & Steel Works Ltd. - Industrial Manufacturer</title>
        <meta property="og:site_name" content="Apex Forgings & Steel Works Ltd." />
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Corporation",
            "name": "Apex Forgings & Steel Works Ltd.",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "Jalan Industrial Complex, Gate 3",
                "addressLocality": "Howrah",
                "postalCode": "711411"
            }
        }
        </script>
    </head>
    <body>
        <h1>Welcome to Apex Forgings</h1>
        <p>Managing Director: Viren Agarwal</p>
        <p>Works: Jalan Industrial Complex, Howrah, West Bengal - 711411</p>
        <p>Contact us at <a href="mailto:viren@apexforgings.in">viren@apexforgings.in</a></p>
        <p>Call our works office: <a href="tel:+913322309601">+91 33 2230 9601</a></p>
        <p>GSTIN: 19AAACA1234A1Z5</p>
    </body>
    </html>
    """
    raw_bytes = sample_html.encode("utf-8")
    expected_hash = hashlib.sha256(raw_bytes).hexdigest()

    crawler = GenuineEvidenceCrawler(allow_private_for_tests=True)

    # Monkeypatch fetch_url to return our sample_html
    def mock_fetch(url):
        return sample_html, 200, expected_hash, None

    monkeypatch.setattr(crawler, "fetch_url", mock_fetch)

    result = crawler.crawl_and_extract("https://apexforgings.in", "apexforgings.in")

    assert result["canonical_domain"] == "apexforgings.in"
    assert result["company_name"] == "Apex Forgings & Steel Works Ltd."
    assert "viren@apexforgings.in" in result["emails"]
    assert result["primary_email"] == "viren@apexforgings.in"
    assert any("3322309601" in p or "913322309601" in p for p in result["phones"])
    assert result["director_name"] == "Viren Agarwal"
    assert "19AAACA1234A1Z5" in result["gstins"]
    assert result["page_hash"] == expected_hash
    assert result["confidence_score"] >= 0.85
    # Strict verification: turnover was not mentioned on site, so it MUST be None!
    assert result["turnover"] is None


def test_campaign_api_lifecycle_and_shortfall():
    client = TestClient(app)

    # 1. Start Campaign
    res = client.post(
        "/api/campaign/start",
        json={
            "prompt": "Howrah foundry casting and fabrication units",
            "target_count": 50,
            "client_id": "lakhotia",
            "campaign_type": "both",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    job_id = data["job_id"]
    assert job_id.startswith("camp_")

    # 2. Status Poll
    status_res = client.get(f"/api/campaign/status/{job_id}")
    assert status_res.status_code == 200
    s_data = status_res.json()
    assert s_data["job_id"] == job_id
    assert s_data["status"] in ("running", "done", "partial")
    assert "audit_metrics" in s_data
    assert "attempted" in s_data["audit_metrics"]

    # 3. Simulate job shortfall (e.g. 1 real lead discovered for requested target 50)
    job = CAMPAIGN_JOBS[job_id]
    job.leads = [
        {
            "company_name": "Apex Steel Casting Pvt. Ltd.",
            "canonical_domain": "apexsteelcasting.in",
            "director_name": "Viren Agarwal",
            "phone": "+919831118255",
            "email": "viren@apexsteelcasting.in",
            "district": "Jalan Industrial Complex, Howrah",
            "state": "West Bengal",
            "estimated_turnover": "Not Disclosed on Website",
            "observed_assets_or_fleet": "Not Disclosed on Website",
            "whatsapp_message_template": "Dear Mr. Viren Agarwal, Matrix 360 Consulting is here.",
            "email_subject": "Accelerating Growth for Apex Steel Casting",
            "email_body": "Dear Mr. Viren Agarwal, we specialize in capital solutions.",
            "qualification_status": "PREPASS",
            "confidence_score": 0.92,
            "verified_source_url": "https://apexsteelcasting.in/contact-us",
            "crawled_urls": "https://apexsteelcasting.in | https://apexsteelcasting.in/contact-us",
            "retrieval_timestamp": "2026-10-23T12:00:00Z",
            "page_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "extraction_methods": "mailto_anchor + schema_org_jsonld",
            "scraped_at": "2026-10-23T12:00:00Z",
        }
    ]
    job.status = "partial"
    job.attempted = 15
    job.fetched = 12
    job.blocked = 2
    job.extracted = 4
    job.qualified = 1
    job.persisted = 1

    # Verify status reports PARTIAL with audit counts
    status_res2 = client.get(f"/api/campaign/status/{job_id}")
    assert status_res2.status_code == 200
    s_data2 = status_res2.json()
    assert s_data2["status"] == "partial"
    assert s_data2["audit_metrics"]["attempted"] == 15
    assert s_data2["audit_metrics"]["blocked"] == 2

    # 4. Export WhatsApp CSV
    wa_res = client.get(f"/api/campaign/export/{job_id}?format=whatsapp")
    assert wa_res.status_code == 200
    assert "text/csv" in wa_res.headers["content-type"]
    wa_text = wa_res.text
    assert "Company_Name,Director_Name,Phone,WhatsApp_Message_Template" in wa_text
    assert "Apex Steel Casting Pvt. Ltd." in wa_text
    assert "+919831118255" in wa_text

    # 5. Export Email CSV
    email_res = client.get(f"/api/campaign/export/{job_id}?format=email")
    assert email_res.status_code == 200
    assert "text/csv" in email_res.headers["content-type"]
    email_text = email_res.text
    assert "Company_Name,Contact_Person,Email,Subject_Line" in email_text
    assert "viren@apexsteelcasting.in" in email_text

    # 6. Export Full Provenance CSV
    prov_res = client.get(f"/api/campaign/export/{job_id}?format=full")
    assert prov_res.status_code == 200
    prov_text = prov_res.text
    assert "Verified_Source_URL" in prov_text
    assert "Page_SHA256" in prov_text
    assert "https://apexsteelcasting.in/contact-us" in prov_text
    assert "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" in prov_text
