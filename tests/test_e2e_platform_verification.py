import io
import json
import csv
from fastapi.testclient import TestClient
from services.api.app import app


def test_full_system_verification():
    client = TestClient(app)

    # 1. Bootstrapping Session
    res_sess = client.post("/api/v1/auth/bootstrap")
    assert res_sess.status_code == 200, f"Bootstrap failed: {res_sess.text}"
    token = res_sess.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert res_sess.json()["role"] == "superadmin"

    # 2. Multi-Client Lead Finder & AI Filter Generation
    clients = ["lakhotia", "shree", "vrindavan", "matrix360_advisory", "apex_industrial_fleet"]
    for cid in clients:
        res = client.post("/api/campaign/generate-filters", json={
            "prompt": f"Targeting criteria for {cid}",
            "client_id": cid
        }, headers=headers)
        assert res.status_code == 200, f"Client {cid} failed with status {res.status_code}: {res.text}"
        data = res.json()
        assert "four_filter_options" in data
        assert "company_sector_choices" in data["four_filter_options"]

    # 3. CV / People Mode Prompt Test
    res_people = client.post("/api/campaign/generate-filters", json={
        "prompt": "A CV person comes in and he want leads for the people who are in high companies and they are earning in very much lakhs",
        "client_id": "shree",
        "lead_mode": "people"
    }, headers=headers)
    assert res_people.status_code == 200
    p_data = res_people.json()
    assert p_data["entity_mode"] == "person"
    assert len(p_data["search_dorks"]) > 0

    # 4. AI Advisor Multi-Client Access
    res_adv = client.post("/api/campaign/ai/advisor-chat", json={
        "message": "Who should we target for Shree Heights luxury residences?",
        "client_id": "shree",
        "current_plan": {}
    }, headers=headers)
    assert res_adv.status_code == 200, f"Advisor failed: {res_adv.text}"
    assert len(res_adv.json()["response_text"]) > 20

    # 5. V5 Workbench Streaming Qualification & Strict Phone Fidelity
    csv_data = """Company_Name,Director_Name,Designation,Mobile,Email,City,Turnover
Lakhotia Heavy Eng,Rajesh Lakhotia,Managing Director,09830012345,rajesh@lakhotia.com,Kolkata,65 Cr
MedHealth Clinic,Dr. Subhash Sen,Chief Medical Officer,9831122334,drsubhash@medhealth.in,Chandannagar,1.2 Cr
Apex Logistics Hub,Pooja Verma,VP Logistics,=cmd|' /C calc'!A0,pooja@apex.com,Howrah,35 Cr
Street Chai Wala,Ramu,Worker,9000000001,ramu@none.com,Kolkata,3 Lakh
"""

    res_wb = client.post("/api/v5/workbench/stream-qualify", data={
        "prompt": "High earning corporate decision makers, directors and medical specialists in Kolkata and Chandannagar",
        "client_id": "shree",
        "chunk_size": 2
    }, files={
        "file": ("companies_test.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")
    }, headers=headers)

    assert res_wb.status_code == 200, f"Workbench stream failed: {res_wb.text}"
    events = []
    for line in res_wb.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    complete_evt = [e for e in events if e.get("event") == "complete"][0]
    reconcile = complete_evt["reconciliation"]
    assert reconcile["reconciliation_valid"] is True
    assert reconcile["raw_rows_received"] == 4

    # 6. Download Qualified CSV & Verify Phone / Injection Fidelity
    dl_url = complete_evt["download_urls"]["qualified_csv"]
    res_dl = client.get(dl_url, headers=headers)
    assert res_dl.status_code == 200
    dl_text = res_dl.content.decode("utf-8-sig")
    assert "09830012345" in dl_text, "Phone number leading zero must be preserved!"
    for row in csv.reader(dl_text.splitlines()):
        for cell in row:
            assert not cell.startswith("="), f"Raw formula found unescaped: {cell}"
