"""Typed numeric filters stay deterministic and never coerce identifiers."""
from __future__ import annotations

import csv
import json

import pytest

from services.api import app, store
from services.api.filter_dsl import FilterValidationError, context_for_fields, evaluate, validate_plan
from services.api.security import User


def test_numeric_boundaries_indian_units_and_identifiers_are_safe():
    context = context_for_fields(
        ["Annual Turnover", "Mobile", "PIN"],
        numeric_fields=["Annual Turnover"],
        numeric_currencies={"Annual Turnover": ["INR"]},
    )
    exact = validate_plan({"field": "Annual Turnover", "operator": "between", "value": ["1 lakh", "1 lakh"]}, context)
    assert evaluate(exact, {"original_fields": {"Annual Turnover": "₹1,00,000.00"}}) is True
    assert evaluate(exact, {"original_fields": {"Annual Turnover": "₹99,999.99"}}) is False
    assert evaluate(exact, {"original_fields": {"Annual Turnover": "not disclosed"}}) is None
    crore = validate_plan({"field": "Annual Turnover", "operator": "gte", "value": "₹1.25 crore"}, context)
    assert evaluate(crore, {"original_fields": {"Annual Turnover": "₹12,500,000"}}) is True
    assert evaluate(crore, {"original_fields": {"Annual Turnover": "$12,500,000"}}) is None
    with pytest.raises(FilterValidationError, match="validated numeric"):
        validate_plan({"field": "Mobile", "operator": "gt", "value": "9000000000"}, context)
    with pytest.raises(FilterValidationError, match="validated numeric"):
        validate_plan({"field": "PIN", "operator": "between", "value": ["100000", "999999"]}, context)


def test_results_use_the_same_typed_numeric_boundary_as_preview(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(app, "RUNTIME_ROOT", tmp_path)
    store.init()
    user = User(username="owner", tenant_id="tenant")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    headers = ["name", "geo_status", "original_fields"]
    with (workspace / "all_records.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for name, turnover in (("boundary-a", "₹1,00,000"), ("boundary-b", "₹100000.00"), ("below", "₹99,999.99"), ("invalid", "unknown")):
            writer.writerow({"name": name, "geo_status": "WB_CONFIRMED", "original_fields": json.dumps({"Annual Turnover": turnover})})
    stats = {"Annual Turnover": {"non_null": 4, "numeric_valid": 3, "numeric_invalid": 1, "numeric_currencies": ["INR"]}}
    schema = {"files": [{"inspection": {"filter_headers": ["Annual Turnover", "Mobile"], "field_stats": stats}}]}
    with store.connect() as conn:
        conn.execute("INSERT INTO datasets(id,tenant_id,uploaded_at,schema_json) VALUES(?,?,?,?)", ("dataset", user.tenant_id, store.now(), json.dumps(schema)))
        plan, _ = app.validate_dataset_filter_plan(conn, "dataset", {"field": "Annual Turnover", "operator": "between", "value": ["1 lakh", "1 lakh"]})
        conn.execute(
            "INSERT INTO jobs(id,tenant_id,dataset_id,idempotency_key,status,created_at,workspace_path,config_json) VALUES(?,?,?,?,?,?,?,?)",
            ("job", user.tenant_id, "dataset", "numeric-boundary-key", "completed", store.now(), str(workspace), json.dumps({"filter_plan": plan})),
        )

    result = app.results("job", user)
    catalog = app.schema_catalog("dataset", user)

    assert result["total"] == 2
    assert {row["name"] for row in result["rows"]} == {"boundary-a", "boundary-b"}
    field = next(item for item in catalog["fields"] if item["header"] == "Annual Turnover")
    assert field["numeric_eligible"] is True
    assert field["numeric_invalid"] == 1
    assert not next(item for item in catalog["fields"] if item["header"] == "Mobile")["numeric_eligible"]
