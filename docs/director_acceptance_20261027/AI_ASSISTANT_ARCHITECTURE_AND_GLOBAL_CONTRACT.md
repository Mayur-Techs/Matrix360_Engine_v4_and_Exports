# AI Assistant Architecture & Global Contract

**Workstream Owner:** Mayur (`Mayur-Techs`)  
**Core Implementation:** `services/api/ai_platform.py`  
**Date:** 27 October 2026  

---

## 1. Global AI Context Contract

The server-authoritative context object governs all assistant interactions:

```python
@dataclass
class GlobalAIContext:
    authenticated_user_id: str
    role: str
    workspace_id: str
    client_id: str
    current_module: str
    selected_record_id: Optional[str] = None
    selected_job_id: Optional[str] = None
    business_profile_version: str = "v1.0"
    objective: str = ""
    module_readiness: Dict[str, str] = field(...)
    allowed_tools: List[str] = field(...)
    ai_provider_status: str = "HEURISTIC_FALLBACK"
```

### Cross-Team Boundaries (Avinash / Romit / Tanmayi)
- **Avinash Shell Boundary:** Mayur delivers an embeddable, modular assistant specification. Avinash owns shared login and global frontend shell integration. Shared capabilities are marked `READY` or `AVINASH_DEFERRED`.
- **Romit Boundary:** Maps ingestion consumes Romit's export contract; the assistant queries Romit sources via read-only tools.
- **Tanmayi Boundary:** Creative studio generation contracts are consumed downstream.

---

## 2. Four Operational Mayur Specialists

1. **Audience Strategy AI (`My Audiences`):**
   - Calibrates commercial objectives, distinguishes B2B/B2C, recommends people-first segments.
2. **Lead Generation AI (`Lead Generation` / `Ask Discovery AI`):**
   - Evaluates search plans, crawler diagnostics, partial job counts, and query phrasing.
3. **Data Cleaning & Intelligence AI (`Data Import`):**
   - Assesses header mappings, identifier text fidelity, deduplication metrics, and Unicode compliance.
4. **Lead Qualification AI (`Qualification`):**
   - Holistically evaluates profile evidence, assigns tiers, and articulates evidence-linked uncertainties.

---

## 3. In-Tool RBAC Registry (10 Operational Tools)

Every tool enforces workspace verification internally (`ctx.assert_can_access_workspace(...)`):

| Tool Name | Scope & Function | Tenant Isolation Mechanism |
|---|---|---|
| `get_workspace_context` | Workspace status & role validation | Asserts caller `workspace_id == target_workspace` |
| `get_jobs` | Active & historical crawler jobs | Filters jobs strictly by caller `client_id` |
| `get_job_status` | Detailed execution metrics for specific job | Asserts job owner matches caller workspace |
| `get_lead_counts` | Total, Prepass, Review, Exclude counts | Queries SQLite ProductionLeadVault scoped to `client_id` |
| `get_data_quality_summary` | Encoding, string fidelity, dedupe summary | Scoped to caller workspace |
| `get_qualification_summary` | Active qualification policy & breakdown | Scoped to caller workspace |
| `get_record_evidence` | Raw observed evidence for specific record | Scoped query in ProductionLeadVault |
| `get_source_health` | Web crawler, Maps adapter, Supabase health | System read-only probe |
| `get_ai_readiness` | Provider state & safety gating | System read-only probe |
| `get_handoff_package_status` | Status of deferred CRM handoff artifact | Asserts caller workspace ownership |
