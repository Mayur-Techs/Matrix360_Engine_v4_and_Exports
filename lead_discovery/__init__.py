"""LeadScope AI Studio — Zero-API Lead Discovery, Qualification & Contact Extraction Package."""
from __future__ import annotations

from .config import EngineConfig
from .agents import (
    PromptFilterAgent,
    DomainDiscoveryAgent,
    QualificationAgent,
    ContactExtractionAgent,
    PlainEnglishFilterSpec,
)
from .discovery_zero_api import (
    KeylessSearchRotator,
    OverpassIndustrialHarvester,
    CrtShHarvester,
    ArchivalIndexHarvester,
    SupplyChainSnowballSpider,
    ObfuscatedContactDecoder,
    HybridScaleOrchestrator,
)
from .crawler import PlaywrightVisualCrawler
from .security import SSRFGuard, TokenBucketRateLimiter, DomainCircuitBreaker, AIKeyGate, WebhookSigner
from .scale_50k_engine import BusinessAndPersonaSynthesizer, CampaignBlueprint
from .integrations import CRMIntegrationHub
from .verified_pilot_data import PILOT_RECORDS, CSV_SHA256

__all__ = [
    "EngineConfig",
    "PromptFilterAgent",
    "DomainDiscoveryAgent",
    "QualificationAgent",
    "ContactExtractionAgent",
    "PlainEnglishFilterSpec",
    "KeylessSearchRotator",
    "OverpassIndustrialHarvester",
    "CrtShHarvester",
    "ArchivalIndexHarvester",
    "SupplyChainSnowballSpider",
    "ObfuscatedContactDecoder",
    "HybridScaleOrchestrator",
    "PlaywrightVisualCrawler",
    "SSRFGuard",
    "TokenBucketRateLimiter",
    "DomainCircuitBreaker",
    "AIKeyGate",
    "WebhookSigner",
    "BusinessAndPersonaSynthesizer",
    "CampaignBlueprint",
    "CRMIntegrationHub",
    "PILOT_RECORDS",
    "CSV_SHA256",
]
