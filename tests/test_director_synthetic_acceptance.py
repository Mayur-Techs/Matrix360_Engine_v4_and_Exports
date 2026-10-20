"""Recovered Director-style synthetic acceptance: real source -> engine -> export.

The historical 100-row fixture was not present in the checkout.  This test is
an explicitly reconstructed synthetic fixture; it does not reuse historical
output counts as engine input.
"""
from __future__ import annotations

import csv
import hashlib
import json

from matrix_engine.engine.core import run
from services.api.filter_dsl import context_for_fields, validate_plan
from services.worker.exporter import create_exports


def _write_source(path) -> None:
    headers = ["Name", "Company", "Industry", "City", "District", "State", "Annual Turnover", "Email"]
    rows = []
    for index in range(21):
        rows.append([f"Howrah Manufacturing {index}", f"Steel Works {index}", "manufacturing", "Howrah", "Howrah", "West Bengal", "₹1,00,000", f"match{index}@example.invalid"])
    rows.extend([
        ["Below boundary", "Steel Works", "manufacturing", "Howrah", "Howrah", "West Bengal", "₹99,999", "below@example.invalid"],
        ["Invalid turnover", "Steel Works", "manufacturing", "Howrah", "Howrah", "West Bengal", "unknown", "invalid@example.invalid"],
        ["Missing district", "Steel Works", "manufacturing", "Howrah", "", "West Bengal", "₹1,00,000", "missing@example.invalid"],
        ["Outside state", "Steel Works", "manufacturing", "Pune", "Pune", "Maharashtra", "₹1,00,000", "outside@example.invalid"],
    ])
    for index in range(75):
        rows.append([f"Other {index}", f"Retail {index}", "retail", "Kolkata", "Kolkata", "West Bengal", "₹2,00,000", f"other{index}@example.invalid"])
    assert len(rows) == 100
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_reconstructed_director_100_row_acceptance_has_21_filtered_lakhotia_exports(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "director_synthetic.csv"
    _write_source(source)

    context = context_for_fields(
        ["State", "District", "Industry", "Annual Turnover"],
        numeric_fields=["Annual Turnover"],
        numeric_currencies={"Annual Turnover": ["INR"]},
    )
    plan = validate_plan({"op": "all", "children": [
        {"field": "State", "operator": "contains", "value": "West Bengal"},
        {"field": "District", "operator": "eq", "value": "Howrah"},
        {"field": "Industry", "operator": "contains", "value": "manufacturing"},
        {"field": "Annual Turnover", "operator": "gte", "value": "1 lakh"},
    ]}, context)

    workspace = tmp_path / "workspace"
    report = run(source_dir, workspace)
    counts, artifacts = create_exports(
        workspace, tmp_path / "exports", "director-synthetic-100", "synthetic-tenant", report["version"],
        client_profiles=("lakhotia",), filter_plan=plan, dataset_name="director_synthetic.csv",
    )

    assert report["reconciled"] is True
    assert report["active_rows"] == 100
    assert counts["Lakhotia"] == 21
    assert counts["Unique_export_candidates"] == 21
    exported = tmp_path / "exports" / "Lakhotia.csv"
    with exported.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 21
    assert {row["district"] for row in rows} == {"Howrah"}
    assert all(json.loads(row["reason_codes"])["lakhotia"] == "OBSERVED_PROFILE_RELEVANCE_ONLY" for row in rows)
    manifest = json.loads((tmp_path / "exports" / "job_manifest.v1.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["Lakhotia"] == 21
    assert manifest["filters"]["filter_plan"] == plan
    assert hashlib.sha256(exported.read_bytes()).hexdigest() == next(item["sha256"] for item in artifacts if item["name"] == "Lakhotia.csv")
