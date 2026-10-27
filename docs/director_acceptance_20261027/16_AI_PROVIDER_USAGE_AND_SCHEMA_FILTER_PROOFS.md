# MATRIX 360 — AI PROVIDER REALITY, COST AUDIT & SCHEMA FILTER PROOFS
**Directory:** `docs/director_acceptance_20261027/16_AI_PROVIDER_USAGE_AND_SCHEMA_FILTER_PROOFS.md`  
**Execution Date:** 27 October 2026  
**Auditor:** Mayur (Principal AI Systems Engineer & Data Architect)  
**Standard:** Truthful Architecture Attribution & Zero PII Leakage

---

## 1. Reality Audit Across All AI Layers: Model-Backed vs. Deterministic Heuristics

Every intelligence layer in Matrix 360 was inspected to determine whether it executes an actual LLM API call, uses deterministic regex/heuristics, or operates in zero-key autonomous mode:

| Layer | Functional Purpose | Actual Implementation Mechanism | Real LLM Provider / Model | Fallback Mechanism When $0 Spend / No Key | Guardrails Against Hallucination & PII | Test Proof |
|---|---|---|---|---|---|---|
| **1. Conversational Objective Extraction** | Extracts target personas, roles, locations from operator chat | Heuristic intent parser with profile calibrator | None (Contextual intent engine in `services/api/campaign_routes.py`) | Deterministic keyword mapping & plan card adjustment | Does not receive private PII; bounded to client targeting scope | `test_director_4_acceptance_tests.py::test_acceptance_test_1_shree_heights` |
| **2. Source Planning & Query Dork Generation** | Generates up to 24 targeted Google/Bing search dorks | Pattern-directed dynamic generator (`PromptQueryAdapter`) | None (Deterministic combinatorial query builder) | 219+ West Bengal seed directory & Bing HTML scraping | Never sends user PII to search engines | `test_200_genuine_ai_crawler.py::test_prompt_query_planner_generates_up_to_24_queries` |
| **3. Web Evidence Fact Extraction** | Extracts verified facts (company, director, phone, email, address) from HTML | REST API caller with JSON schema enforcement (`AILeadExtractionAgent`) | OpenAI `gpt-4o-mini` or Google Gemini `gemini-2.5-flash` | Crawl4AI markdown pruner + DOM table & JSON-LD heuristic extractor | Strict Zero Fabrication: If phone/email not in HTML, kept empty; no synthetic promoter names | `test_200_genuine_ai_crawler.py::test_crawl4ai_markdown_pruner_and_ai_extraction` |
| **4. Schema / Header / Alias Mapping** | Maps messy Indian business column headers to canonical schema | Multi-tier agent: Exact -> Fuzzy Levenshtein -> Fingerprinting -> Learned store (`SemanticAliasAgent`) | Planned for LLM ambiguous resolution; currently 100% deterministic code | Fingerprint regex on email, phone, GST, PAN, vehicle registration | Works strictly on anonymized header strings; zero dataset rows transmitted | `tests/test_v5_engine.py::test_v5_semantic_alias_layer1_exact_and_fuzzy` |
| **5. Three Editable Plan Cards** | Discovery (A), Qualification (B), AI Assessment (C) | Structured schema populated from client brand JSON profiles | Deterministic schema binding | Static profile defaults per brand | Cards are fully editable by operator; AI suggestions cannot silently override | `test_director_4_acceptance_tests.py` |
| **6. Typed Nested Filter DSL** | Complex boolean logic (AND/OR/NOT, nulls, ranges, numbers) | Typed AST compiler (`services/api/filter_dsl.py`) | Deterministic Python compiler | Type-safe SQL predicate builder | Enforces numeric types, prevents SQL injection, guarantees reproducibility | `tests/test_filter_dsl.py`, `tests/test_numeric_filter_contract.py` |
| **7. Whole-Profile Qualification** | Evaluates person/org profile against client qualification rules | Multi-criteria scoring agent (`qualify_and_score_lead`) | Deterministic rule & affluence engine (`agentic_company_qualifier.py`) | Rule-based scoring with fit reasons & uncertainty flags | Explanations explicitly cite observed evidence URLs | `tests/test_v5_engine.py::test_v5_agentic_qualifier_inr_parsing` |
| **8. Export Integrity & Provenance Review** | Assures exported records have source URLs and verified status | Deterministic CSV/Parquet export filter pipeline | None | Rule-based suppression of unverified rows | Neutralizes spreadsheet formula injection (`'\t=...`) | `tests/test_2_3m_chunking_and_fidelity.py::test_csv_formula_injection_defense` |

---

## 2. Model Version, Spend & Boundary Governance

1. **Spend Authorization Guard:**
   * Controlled by `MATRIX_AI_SPEND_APPROVED = false` and `MATRIX_AI_MAX_CALLS = 0` in `services/api/settings.py`.
   * Live paid calls to OpenAI (`gpt-4o-mini`, $0.15 / 1M input tokens) or Google Gemini (`gemini-2.5-flash`, $0.075 / 1M input tokens) are only executed when explicit API keys are injected and `AI_SPEND_APPROVED=true`.
   * **Under default local and staging operation, API spend is strictly \$0.00.**
2. **PII Isolation Boundary:**
   * Raw customer datasets (e.g. 2.3M raw rows) are **NEVER** sent to third-party LLMs.
   * LLMs only receive compact markdown snippets (<2,400 characters) pruned of scripts and styles from public websites for fact extraction.

---

## 3. Typed Nested Filter DSL Verification

The Filter DSL supports recursive expressions with strict type validation:

```json
{
  "op": "and",
  "conditions": [
    {"field": "district", "op": "in", "value": ["Howrah", "Hooghly"]},
    {
      "op": "or",
      "conditions": [
        {"field": "turnover_inr", "op": "gte", "value": 50000000},
        {"field": "vehicle_type", "op": "eq", "value": "COMMERCIAL_FLEET"}
      ]
    },
    {"field": "named_contact", "op": "is_not_null", "value": null}
  ]
}
```

* **Numeric Range Handling:** Correctly handles Indian numbering systems (Crores, Lakhs) without numeric precision truncation.
* **Tested Status:** Verified across `tests/test_filter_dsl.py` and `tests/test_numeric_filter_contract.py`.
