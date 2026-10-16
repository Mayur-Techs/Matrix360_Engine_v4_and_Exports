"""Bounded provider seam for optional, non-authoritative AI review suggestions."""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class ReviewProvider(Protocol):
    def suggest(self, evidence: dict[str, str]) -> dict[str, str]: ...


@dataclass
class DisabledProvider:
    reason: str

    def suggest(self, evidence: dict[str, str]) -> dict[str, str]:
        return {"status": "DISABLED", "reason": self.reason}


class OpenAIReviewProvider:
    """Uses Responses with non-PII evidence only. Suggestions never promote a class."""
    def __init__(self, model: str) -> None:
        self.model = model
        self.key = os.environ.get("OPENAI_API_KEY", "")
        if not self.key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

    def suggest(self, evidence: dict[str, str]) -> dict[str, str]:
        payload = {
            "model": self.model,
            "store": False,
            "input": [{"role": "system", "content": [{"type": "input_text", "text": "Assess only whether this de-identified record needs manual data-quality review. Do not infer buyer intent, consent, wealth, identity, or geography. Return JSON with decision REVIEW or NO_REVIEW and a short reason."}]}, {"role": "user", "content": [{"type": "input_text", "text": json.dumps(evidence, sort_keys=True)}]}],
            "text": {"format": {"type": "json_schema", "name": "matrix_review", "strict": True, "schema": {"type": "object", "properties": {"decision": {"type": "string", "enum": ["REVIEW", "NO_REVIEW"]}, "reason": {"type": "string"}}, "required": ["decision", "reason"], "additionalProperties": False}}},
        }
        request = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310: fixed provider endpoint
            response_json = json.loads(response.read())
        output_text = response_json.get("output_text", "{}")
        result = json.loads(output_text)
        return {"status": "SUGGESTION_REQUIRES_REVIEW", "decision": result["decision"], "reason": result["reason"]}


def build_provider(enabled: bool, provider_name: str, model: str, max_calls: int) -> ReviewProvider:
    if not enabled or max_calls <= 0:
        return DisabledProvider("AI_DISABLED_OR_ZERO_CALL_LIMIT")
    if provider_name != "openai":
        return DisabledProvider("UNSUPPORTED_PROVIDER")
    return OpenAIReviewProvider(model)
