"""Matrix 360 V5 Engine Package.

Provides:
- SemanticAliasAgent: 3-Layer Hybrid Resolution Pipeline for zero-hardcode schema & alias resolution.
- AgenticCompanyQualifier: Dynamic universal brand qualification, multi-choice company filters, and affluence / vehicle / turnover ranking.
- DualDriveCloudBridge: Input Drive data lake watcher + stateless worker + Output Drive vault publisher.
"""
from __future__ import annotations

from .semantic_alias_agent import (
    CANONICAL_ONTOLOGY,
    ColumnMappingResult,
    SemanticAliasAgent,
    fingerprint_values,
    normalize_token_string,
)
from .agentic_company_qualifier import (
    VEHICLE_VALUATION_CATALOG,
    ROLE_SENIORITY_WEIGHTS,
    evaluate_vehicle_profile,
    generate_multichoice_company_filters,
    parse_inr_amount,
    qualify_and_score_lead,
)
from .dual_drive_pipeline import DualDriveCloudBridge

__version__ = "5.0.0"
__all__ = [
    "CANONICAL_ONTOLOGY",
    "ColumnMappingResult",
    "SemanticAliasAgent",
    "fingerprint_values",
    "normalize_token_string",
    "VEHICLE_VALUATION_CATALOG",
    "ROLE_SENIORITY_WEIGHTS",
    "evaluate_vehicle_profile",
    "generate_multichoice_company_filters",
    "parse_inr_amount",
    "qualify_and_score_lead",
    "DualDriveCloudBridge",
    "__version__",
]
