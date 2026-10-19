"""Bounded AI research review must preserve privacy and deterministic classes."""
from __future__ import annotations

import csv
import json

from services.worker import runner


def test_ai_review_uses_business_evidence_only(tmp_path, monkeypatch):
    source = tmp_path / "all_records.csv"
    fields = ["source_record_id", "name", "phone_source", "email_normalized", "address", "company", "sector", "district", "geo_status", "lakhotia_class", "shree_class", "vrindavan_class"]
    with source.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"source_record_id": "record-1", "name": "Private Name", "phone_source": "9876543210", "email_normalized": "private@example.test", "address": "Private Street", "company": "Acme Steel", "sector": "manufacturing", "district": "Howrah", "geo_status": "WB_CONFIRMED", "lakhotia_class": "N", "shree_class": "N", "vrindavan_class": "N"})

    seen = []
    monkeypatch.setattr("engine.ai.suggest", lambda evidence: seen.append(evidence) or {"project": "lakhotia", "evidence_quote": "Acme Steel", "reason": "Observed company signal"})

    result = runner.generate_ai_review(source, tmp_path, 1)

    assert result == {"ai_review_candidates": 1, "ai_review_calls": 1, "ai_review_suggestions": 1}
    assert "Private Name" not in seen[0] and "9876543210" not in seen[0] and "Private Street" not in seen[0]
    suggestion = json.loads((tmp_path / "ai_review_suggestions.jsonl").read_text(encoding="utf-8"))
    assert suggestion == {"source_record_id": "record-1", "suggestion": "lakhotia", "status": "SUGGESTION_REQUIRES_REVIEW"}
