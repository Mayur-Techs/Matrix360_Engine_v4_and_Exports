"""Tests for Matrix 360 Consulting live scraping campaign engine and export formats."""
import time
from fastapi.testclient import TestClient
from services.api.app import app
from services.api.campaign_routes import (
    _clean_phone,
    _derive_director_name,
    _infer_district,
    _format_company_name,
    CAMPAIGN_JOBS,
    CampaignJob,
)


def test_clean_phone_formatting():
    assert _clean_phone("9831118255") == "+919831118255"
    assert _clean_phone("+919007211599") == "+919007211599"
    assert _clean_phone("09831118255") == "+919831118255"
    assert _clean_phone("919831118255") == "+919831118255"


def test_derive_director_name():
    # From email
    assert "Viren" in _derive_director_name("viren@anilbalajisteel.com", "", "anilbalajisteel.com")
    # From generic email
    assert "Managing Director" in _derive_director_name("sales@company.com", "", "company.com")
    # From title
    assert "Rajesh" in _derive_director_name("info@company.com", "Contact Mr. Rajesh Agarwal, Plant Head", "company.com")


def test_infer_district():
    assert _infer_district("Jalan Industrial Complex Howrah West Bengal") == "Howrah"
    assert _infer_district("Dankuni logistics park Hooghly") == "Hooghly"
    assert _infer_district("Raniganj Durgapur steel fabrication") == "Paschim Bardhaman"


def test_format_company_name():
    assert "Balaji Steel" in _format_company_name("anilbalajisteel.com", "Anil Balaji Steel - Contact Us")
    assert "Gem Allied" in _format_company_name("gem-allied.com", "")


def test_campaign_api_lifecycle():
    client = TestClient(app)

    # 1. Start Campaign
    res = client.post(
        "/api/campaign/start",
        json={
            "prompt": "Howrah foundry casting and fabrication units",
            "target_count": 10,
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
    assert s_data["status"] in ("running", "done")

    # 3. Create mock leads in the job to test all export formats thoroughly
    CAMPAIGN_JOBS[job_id].leads = [
        {
            "company_name": "Apex Steel Casting Pvt. Ltd.",
            "canonical_domain": "apexsteelcasting.in",
            "director_name": "Viren Agarwal (Director)",
            "phone": "+919831118255",
            "email": "viren@apexsteelcasting.in",
            "district": "Howrah",
            "state": "West Bengal",
            "estimated_turnover": "₹ 25 Cr – ₹ 120 Cr",
            "observed_assets_or_fleet": "Commercial Fleets & Heavy Machinery",
            "whatsapp_message_template": "Hi Viren, Matrix 360 Consulting is here.",
            "email_subject": "Accelerating Growth for Apex Steel Casting",
            "email_body": "Dear Viren, we specialize in capital solutions.",
            "qualification_status": "PREPASS",
            "confidence_score": 0.92,
            "scraped_at": "2026-10-23T12:00:00Z",
        }
    ]

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
    email_text = email_res.text
    assert "Company_Name,Contact_Person,Email,Subject_Line,Email_Body_Opening" in email_text
    assert "viren@apexsteelcasting.in" in email_text
    assert "Accelerating Growth for Apex Steel Casting" in email_text

    # 6. Export Full CSV
    full_res = client.get(f"/api/campaign/export/{job_id}?format=full")
    assert full_res.status_code == 200
    full_text = full_res.text
    assert "Company,District,State,Director_Name,Phone,Email,Domain" in full_text
    assert "apexsteelcasting.in" in full_text

    # 7. List campaigns
    jobs_res = client.get("/api/campaign/jobs")
    assert jobs_res.status_code == 200
    assert any(c["job_id"] == job_id for c in jobs_res.json()["campaigns"])
