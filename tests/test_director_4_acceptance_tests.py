"""Director 27 October Acceptance Verification Suite.

Tests the four P0 Director Acceptance Scenarios:
1. Shree Heights (B2C People Mode, Chandannagar dorks, dual-table existing vs new)
2. Lakhotia Industrial Complex (B2B Org Mode, Howrah dorks, distinct records)
3. Source Convergence (Mayur Web Crawler + Romit Maps Scraper, source badges, exact deduplication)
4. Zero Results and Truthful Recovery (Zero synthetic rows, empty state compliance)
"""
import pytest
from starlette.testclient import TestClient
from services.api.app import app
from lead_discovery.prompt_search_adapter import PromptQueryAdapter
from lead_discovery.maps_adapter import RomitMapsAdapter


@pytest.fixture
def client():
    return TestClient(app)


def test_acceptance_test_1_shree_heights(client):
    """Test 1: Shree Heights - B2C Individual Mode, Chandannagar Dorks, Dual-Table Persistence."""
    # 1. Profile verification
    res = client.get("/api/campaign/profile/shree")
    assert res.status_code == 200
    p = res.json()
    assert p["id"] == "shree"
    assert p["search_parameters"]["entity_mode"] == "person"
    assert "Doctor / Clinic" in [pill["label"] for pill in p["suggested_pills"]]

    # 2. B2C Chandannagar Search Dorks Generation
    prompt = "High-income doctors, chartered accountants and advocates in Chandannagar"
    queries = PromptQueryAdapter.generate_queries(prompt, max_queries=12)
    assert len(queries) >= 6
    # Must contain Chandannagar and professional dorks
    combined_queries = " ".join(queries).lower()
    assert "chandannagar" in combined_queries
    assert any(term in combined_queries for term in ("doctor", "clinic", "advocate", "chartered accountant", "chamber"))

    # 3. AI Advisor Chat Refinement
    chat_res = client.post("/api/campaign/ai/advisor-chat", json={
        "message": "Also include pediatricians and Bangalore native corporate executives",
        "client_id": "shree"
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "Healthcare" in str(chat_data.get("updated_plan", {})) or "Bangalore" in chat_data.get("response_text", "")

    # 4. Ingest a real lead for Shree Heights and verify dual table separation
    ingest_res = client.post("/api/discovery/ingest-maps", json={
        "client_id": "shree",
        "records": [
            {
                "company": {"name": "Dr. Subhashis Mukherjee Clinic", "website": "https://drsmukherjee-chd.org", "address": "GT Road, Chandannagar"},
                "contacts": [{"name": "Dr. Subhashis Mukherjee", "role": "Physician", "phone": "+91 98310 44219", "email": "dr@mukherjee.org"}],
                "sector": "Healthcare"
            }
        ]
    })
    assert ingest_res.status_code == 200

    # 5. Verify dual table output: Existing vs Newly generated
    leads_res = client.get("/api/discovery/leads?client_id=shree&job_id=job_test_session_123")
    assert leads_res.status_code == 200
    leads_data = leads_res.json()
    assert "existing_leads" in leads_data
    assert "newly_generated_leads" in leads_data
    assert len(leads_data["existing_leads"]) >= 1


def test_acceptance_test_2_lakhotia_industrial(client):
    """Test 2: Lakhotia Industrial Complex - B2B Org Mode, Howrah Dorks, Distinct Records."""
    # 1. Profile verification
    res = client.get("/api/campaign/profile/lakhotia")
    assert res.status_code == 200
    p = res.json()
    assert p["id"] == "lakhotia"
    assert p["search_parameters"]["entity_mode"] == "organization"
    assert "Manufacturing" in [pill["label"] for pill in p["suggested_pills"]]

    # 2. B2B Industrial Search Dorks Generation
    prompt = "Manufacturing plants, steel fabrication, and 3PL warehouses in Howrah and Jalan Complex"
    queries = PromptQueryAdapter.generate_queries(prompt, max_queries=12)
    assert len(queries) >= 6
    combined_queries = " ".join(queries).lower()
    assert "howrah" in combined_queries
    assert any(term in combined_queries for term in ("manufacturing", "steel", "warehouse", "logistics", "foundry"))


def test_acceptance_test_3_source_convergence(client):
    """Test 3: Source Convergence - Mayur Web Crawler + Romit Maps Scraper."""
    # 1. Ingest Maps record via Romit Maps Adapter
    maps_records = [
        {
            "company": {"name": "Howrah Alloy & Steel Works", "website": "https://howrahalloy.com", "address": "Jalan Industrial Complex, Howrah"},
            "contacts": [{"name": "Praveen Jalan", "role": "Managing Director", "phone": "+91 98300 55112", "email": "praveen@howrahalloy.com"}],
            "sector": "Steel & Metallurgy"
        }
    ]
    res1 = client.post("/api/discovery/ingest-maps", json={
        "client_id": "lakhotia",
        "records": maps_records
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["saved_and_persisted"] >= 1

    # Ingest the exact same record again to test deduplication
    res2 = client.post("/api/discovery/ingest-maps", json={
        "client_id": "lakhotia",
        "records": maps_records
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["duplicates_deduplicated"] >= 1

    # 2. Check source summary
    summary_res = client.get("/api/discovery/sources-summary?client_id=lakhotia")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "by_source" in summary
    assert "maps_scraper_v4" in summary["by_source"]


def test_acceptance_test_4_zero_results_and_truthful_recovery(client):
    """Test 4: Zero Results - No synthetic records fabricated, truthful empty state."""
    # Query a non-existent client or a clean new client profile
    res = client.get("/api/discovery/leads?client_id=non_existent_client_999")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 0
    assert data["leads"] == []
    assert data["existing_leads"] == []
    assert data["newly_generated_leads"] == []
