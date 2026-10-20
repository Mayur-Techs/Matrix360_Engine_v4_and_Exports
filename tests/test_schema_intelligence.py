"""Header-only filter catalog tests."""
from __future__ import annotations

import json

from services.api import app, store
from services.api import schema_intelligence
from services.api.schema_intelligence import build_catalog
from services.api.security import User


def test_catalog_preserves_contact_constants_and_groups_business_attributes():
    catalog = build_catalog(["Name", "Email", "Mobile No", "Address", "Company Name", "Designation", "Industry Segment", "Vehicle Make"])
    by_header = {item["header"]: item for item in catalog}

    assert by_header["Name"]["fixed"] is True
    assert by_header["Email"]["ai_eligible"] is False
    assert by_header["Company Name"]["group_id"] == "company"
    assert by_header["Designation"]["group_id"] == "role"
    assert by_header["Industry Segment"]["group_id"] == "industry"
    assert by_header["Vehicle Make"]["group_id"] == "asset"


def test_schema_catalog_uses_all_previously_inspected_worksheet_headers(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    schema = {"files": [{"inspection": {"headers": ["Name"], "filter_headers": ["Name", "Company Name", "Industry Segment"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-1", user.tenant_id, store.now(), json.dumps(schema)))

    result = app.schema_catalog("dataset-1", user)

    assert result["summary"]["fixed_fields"] == 1
    assert result["summary"]["filter_fields"] == 2
    assert {item["header"] for item in result["fields"]} == {"Name", "Company Name", "Industry Segment"}


def test_schema_ai_endpoint_audits_only_header_count(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "suggest_catalog_refinements", lambda catalog: [{"header": "Industry", "group": "Industry and operating profile", "label": "Industry", "reason": "Observed sector attribute."}])
    store.init()
    user = User(username="owner", tenant_id="tenant")
    schema = {"files": [{"inspection": {"filter_headers": ["Name", "Industry"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-ai", user.tenant_id, store.now(), json.dumps(schema)))

    result = app.schema_ai_suggestions("dataset-ai", user)
    with store.connect() as conn:
        event = conn.execute("SELECT details_json FROM audit_events WHERE entity_id=?", ("dataset-ai",)).fetchone()

    assert result["suggestions"][0]["header"] == "Industry"
    assert json.loads(event["details_json"]) == {"eligible_header_count": 1}


def test_ai_refinement_transmits_only_non_contact_headers(monkeypatch):
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return json.dumps({"output_text": json.dumps({"suggestions": [{"header": "Industry", "group": "Industry and operating profile", "label": "Industry", "reason": "Sector field."}]})}).encode()

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data)
        return Response()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("MATRIX_SCHEMA_AI_ENABLED", "true")
    monkeypatch.setattr(schema_intelligence.urllib.request, "urlopen", fake_urlopen)

    suggestions = schema_intelligence.suggest_catalog_refinements(build_catalog(["Name", "Email", "Address", "Industry"]))

    assert json.loads(captured["payload"]["input"]) == {"headers": ["Industry"]}
    assert suggestions == [{"header": "Industry", "group": "Industry and operating profile", "label": "Industry", "reason": "Sector field."}]


def test_responses_output_text_supports_raw_http_response_shape():
    result = {"output": [{"type": "message", "content": [{"type": "output_text", "text": '{"ok":true}'}]}]}

    assert schema_intelligence.responses_output_text(result) == '{"ok":true}'
