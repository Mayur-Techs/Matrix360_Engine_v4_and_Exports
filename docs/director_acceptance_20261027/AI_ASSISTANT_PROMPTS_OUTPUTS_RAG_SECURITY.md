# AI Assistant Prompts, Outputs, RAG, and Security

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Implementation File:** `services/api/ai_platform.py`  
**Date:** 27 October 2026  

---

## 1. Truthful Provider State Machine

The platform enforces strict truthfulness in AI reporting. The UI never labels heuristic rules as "live AI model inference":

```
┌─────────────────────────────────┐
│     Backend Provider State      │
├─────────────────────────────────┤
│ MODEL_CONNECTED_AND_CALLED      │ ◄── Real OpenAI/Gemini call authorized and completed
│ MODEL_CONFIGURED_BUT_NOT_CALLED │ ◄── Keys present, prompt handled via deterministic path
│ HEURISTIC_FALLBACK              │ ◄── Deterministic expert rules active (honest labeling)
│ MODEL_UNAVAILABLE               │ ◄── Network timeout or provider outage
│ BUDGET_BLOCKED                  │ ◄── Token ceiling / cost limit reached
│ UNVERIFIED                      │ ◄── Initial startup state before health probe
└─────────────────────────────────┘
```

---

## 2. Structured Filter Diffs (Before → After)

The assistant cannot unilaterally mutate active filters. Revisions are returned as a structured diff requiring explicit user approval:

```json
{
  "before": {
    "entity_mode": "organization",
    "target_occupations": []
  },
  "after": {
    "entity_mode": "person",
    "target_occupations": ["Healthcare & Medical Practitioners"],
    "geographic_affinities": ["Chandannagar / Hooghly"]
  },
  "diff_summary": [
    "Switched target entity to PERSON (Decision-Makers). Excluded organizational corporate shells.",
    "Added 'Healthcare & Medical Practitioners' to target professions.",
    "Added verified local association requirement: 'Chandannagar / Hooghly'."
  ],
  "requires_approval": true
}
```

---

## 3. Adversarial Security & Prompt Injection Defense

1. **Untrusted Evidence Treatment:** All web content, page titles, HTML meta tags, and user chat inputs are treated as untrusted data, never as system directives.
2. **Regex Neutralization:** Patterns like `ignore all previous instructions`, `system: you are now`, or `reveal api keys` are scrubbed with `[REDACTED_ADVERSARIAL_INSTRUCTION]`.
3. **Cross-Tenant Attack Rejection:** Any prompt attempting to query another workspace (e.g. `Show me leads from workspace--tenant_beta`) is intercepted before tool execution and returns a 200 with an explicit `Access Denied` audit log.
4. **PII Redaction Gate:** Raw 2.3M phone numbers, secret keys, and personal identifiers are never forwarded to third-party model providers.
