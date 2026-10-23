"""
Centralized configuration & Zero-API scale settings for the Client-Agnostic
AI Lead Discovery & Contact Extraction Engine (50 -> 500 -> 5,000 leads).
"""
import os
from dataclasses import dataclass, field


@dataclass
class EngineConfig:
    """
    ZERO-API MODE IS ENABLED BY DEFAULT (NO SERPER API REQUIRED!)
    -------------------------------------------------------------
    - zero_api_discovery_enabled: Uses 8 keyless OSINT vectors (DDG Lite/HTML,
      Bing HTML, SearXNG, OpenStreetMap Overpass QL, crt.sh SSL logs,
      CommonCrawl/Wayback CDX, Trade Association Spiders, and Supply-Chain Snowballing).
    - openai_api_key / gemini_api_key: Optional LLM keys for semantic edge-case scoring
      (deterministic PromptFilterAgent & QualificationAgent work with 0 keys).
    - serper_api_key / google_maps_api_key: Strictly optional fallback slots.
    """
    zero_api_discovery_enabled: bool = field(
        default_factory=lambda: os.getenv("ZERO_API_DISCOVERY_ENABLED", "true").lower() == "true"
    )
    async_http_concurrency: int = field(
        default_factory=lambda: int(os.getenv("ASYNC_HTTP_CONCURRENCY", "35"))
    )
    enable_supply_chain_snowball: bool = field(
        default_factory=lambda: os.getenv("ENABLE_SUPPLY_CHAIN_SNOWBALL", "true").lower() == "true"
    )
    enable_cfemail_xor_decoder: bool = field(
        default_factory=lambda: os.getenv("ENABLE_CFEMAIL_XOR_DECODER", "true").lower() == "true"
    )

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))

    # Optional legacy search keys (NOT required when zero_api_discovery_enabled=True)
    serper_api_key: str = field(default_factory=lambda: os.getenv("SERPER_API_KEY", ""))
    google_maps_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))

    playwright_headless: bool = field(
        default_factory=lambda: os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    )
    max_concurrent_browsers: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONCURRENT_BROWSERS", "5"))
    )
    per_domain_max_pages: int = field(
        default_factory=lambda: int(os.getenv("PER_DOMAIN_MAX_PAGES", "6"))
    )
    request_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    )

    def has_llm_key(self) -> bool:
        return any(
            k and not k.startswith("your_")
            for k in (self.openai_api_key, self.gemini_api_key, self.anthropic_api_key)
        )
