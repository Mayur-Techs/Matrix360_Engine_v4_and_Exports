"""Schema-aware audience filters stay parameterized and data-backed."""
from __future__ import annotations

import csv
import json

from openpyxl import Workbook

from services.api import app, store
from services.api.security import User


def test_results_support_normalized_and_imported_field_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    dataset_id, job_id = "dataset-1", "job-1"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    headers = ["name", "company", "city", "email_normalized", "geo_status", "district", "lakhotia_class", "shree_class", "vrindavan_class", "vehicle_make", "vehicle_model", "original_fields"]
    with (workspace / "all_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"name": "Sample A", "company": "Acme", "city": "Howrah", "email_normalized": "", "geo_status": "WB_CONFIRMED", "district": "Howrah", "lakhotia_class": "N", "shree_class": "N", "vrindavan_class": "N", "vehicle_make": "Tata", "vehicle_model": "Nexon", "original_fields": json.dumps({"Vehicle Make": "Tata", "Vehicle Model": "Nexon"})})
        writer.writerow({"name": "Sample B", "company": "Beta", "city": "Howrah", "email_normalized": "", "geo_status": "WB_CONFIRMED", "district": "Howrah", "lakhotia_class": "N", "shree_class": "N", "vrindavan_class": "N", "vehicle_make": "Mahindra", "vehicle_model": "XUV", "original_fields": json.dumps({"Vehicle Make": "Mahindra", "Vehicle Model": "XUV"})})
    schema = {"files": [{"inspection": {"headers": ["Vehicle Make", "Vehicle Model", "Company"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", (dataset_id, user.tenant_id, store.now(), json.dumps(schema)))
        conn.execute("INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path) VALUES(?,?,?,?,?,?,?)", (job_id, user.tenant_id, dataset_id, "advanced-filter-key", "completed", store.now(), str(workspace)))

    normalized = app.results(job_id, user, advanced_filters=json.dumps([{"field": "vehicle_make", "operator": "contains", "values": ["tata"]}]))
    imported = app.results(job_id, user, advanced_filters=json.dumps([{"field": "Vehicle Model", "operator": "is_any_of", "values": ["Nexon"]}]))
    metadata = app.filter_metadata(job_id, user)

    assert normalized["total"] == 1
    assert normalized["rows"][0]["vehicle_model"] == "Nexon"
    assert imported["total"] == 1
    assert next(item for item in metadata["fields"] if item["id"] == "vehicle_make")["available_records"] == 2
    assert "Vehicle Model" in metadata["imported_fields"]


def test_saved_nested_filter_plan_limits_job_results(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    headers = ["name", "state", "geo_status", "original_fields"]
    with (workspace / "all_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerow({"name": "A", "state": "West Bengal", "geo_status": "WB_CONFIRMED", "original_fields": json.dumps({"Industry": "manufacturing"})})
        writer.writerow({"name": "B", "state": "West Bengal", "geo_status": "WB_CONFIRMED", "original_fields": json.dumps({"Industry": "retail"})})
    plan = {"op": "all", "children": [{"field": "state", "operator": "eq", "value": "West Bengal"}, {"field": "Industry", "operator": "contains", "value": "manufacturing"}]}
    schema = {"files": [{"inspection": {"filter_headers": ["Industry"]}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset-plan", user.tenant_id, store.now(), json.dumps(schema)))
        conn.execute("INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,config_json) VALUES(?,?,?,?,?,?,?,?)", ("job-plan", user.tenant_id, "dataset-plan", "plan-filter-key", "completed", store.now(), str(workspace), json.dumps({"filter_plan": plan})))
    result = app.results("job-plan", user)
    assert result["total"] == 1
    assert result["rows"][0]["name"] == "A"


def test_upload_inspection_makes_all_worksheet_headers_available_to_filters(tmp_path):
    workbook = Workbook()
    workbook.active.append(["Name", "Company"])
    second = workbook.create_sheet("Vehicle data")
    second.append(["Vehicle Make", "Vehicle Model"])
    source = tmp_path / "multi-sheet.xlsx"
    workbook.save(source)

    inspection = app.inspect_upload(source)

    assert inspection["headers"] == ["Name", "Company"]
    assert {"Name", "Company", "Vehicle Make", "Vehicle Model"} <= set(inspection["filter_headers"])
