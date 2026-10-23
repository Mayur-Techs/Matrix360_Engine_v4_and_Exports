"""
Production Security, Safety & Worst-Case Resilience Layer (`security.py`)
"""
import hashlib
import hmac
import ipaddress
import socket
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
CLOUD_METADATA_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.goog",
    "100.100.100.200",
}


class SSRFGuard:
    @staticmethod
    def is_ip_forbidden(ip_str: str) -> Tuple[bool, Optional[str]]:
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_link_local or ip_str == "169.254.169.254":
                return True, "LINK_LOCAL_METADATA_IP_BLOCKED"
            if ip.is_loopback:
                return True, "LOOPBACK_IP_BLOCKED"
            if ip.is_private:
                return True, "PRIVATE_IP_BLOCKED"
            if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                return True, "RESERVED_IP_BLOCKED"
            return False, None
        except ValueError:
            return False, None

    @classmethod
    def validate_url(cls, url: str, resolve_dns: bool = False) -> Tuple[bool, str]:
        raw = (url or "").strip()
        if not raw:
            return False, "EMPTY_URL"
        if len(raw) > 2048:
            return False, "URL_EXCEEDS_MAX_LENGTH_2048"

        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        scheme = (parsed.scheme or "").lower()
        if scheme not in ALLOWED_SCHEMES:
            return False, f"FORBIDDEN_SCHEME_{scheme.upper()}"

        host = (parsed.hostname or "").lower().strip(".")
        if not host:
            return False, "INVALID_HOSTNAME"

        if host in CLOUD_METADATA_HOSTS or host.endswith(".internal") or host.endswith(".local"):
            return False, "CLOUD_METADATA_OR_INTERNAL_HOST_BLOCKED"

        forbidden, reason = cls.is_ip_forbidden(host)
        if forbidden:
            return False, reason or "FORBIDDEN_IP"

        if resolve_dns:
            try:
                infos = socket.getaddrinfo(host, None)
                for info in infos:
                    resolved_ip = info[4][0]
                    is_bad, bad_reason = cls.is_ip_forbidden(resolved_ip)
                    if is_bad:
                        return False, f"DNS_REBINDING_{bad_reason}"
            except socket.gaierror:
                return False, "DNS_RESOLUTION_FAILED"

        return True, "OK"


class TokenBucketRateLimiter:
    def __init__(self, rate_per_sec: float = 5.0, capacity: float = 15.0):
        self.rate = rate_per_sec
        self.capacity = capacity
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        tokens, last_ts = self._buckets.get(key, (self.capacity, now))
        elapsed = max(0.0, now - last_ts)
        tokens = min(self.capacity, tokens + elapsed * self.rate)
        if tokens >= cost:
            self._buckets[key] = (tokens - cost, now)
            return True
        self._buckets[key] = (tokens, now)
        return False


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float = 0.0
    last_reason: str = ""


class DomainCircuitBreaker:
    def __init__(self, max_failures: int = 2, cooldown_seconds: float = 300.0):
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds
        self._states: Dict[str, CircuitState] = {}

    def can_attempt(self, domain: str) -> Tuple[bool, Optional[str]]:
        st = self._states.get(domain)
        if not st or st.failures < self.max_failures:
            return True, None
        elapsed = time.monotonic() - st.opened_at
        if elapsed >= self.cooldown_seconds:
            st.failures = 0
            return True, None
        return False, f"CIRCUIT_OPEN ({st.last_reason})"

    def record_failure(self, domain: str, reason: str) -> None:
        st = self._states.setdefault(domain, CircuitState())
        st.failures += 1
        st.last_reason = reason
        if st.failures >= self.max_failures:
            st.opened_at = time.monotonic()

    def record_success(self, domain: str) -> None:
        if domain in self._states:
            del self._states[domain]


class AIKeyGate:
    @staticmethod
    def verify_ai_key(
        openai_key: str = "",
        gemini_key: str = "",
        anthropic_key: str = "",
    ) -> Tuple[bool, str, str]:
        for provider, key in (
            ("openai", (openai_key or "").strip()),
            ("gemini", (gemini_key or "").strip()),
            ("anthropic", (anthropic_key or "").strip()),
        ):
            if len(key) >= 12 and not key.startswith("your_"):
                return True, provider, AIKeyGate.mask_secret(key)
        return False, "none", ""

    @staticmethod
    def mask_secret(secret: str) -> str:
        s = (secret or "").strip()
        if len(s) <= 8:
            return "****" if s else ""
        return f"{s[:4]}...{s[-4:]}"


class WebhookSigner:
    @staticmethod
    def sign_payload(payload_bytes: bytes, secret: str) -> str:
        key = (secret or "default-webhook-secret").encode("utf-8")
        digest = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    @staticmethod
    def verify_signature(payload_bytes: bytes, secret: str, signature_header: str) -> bool:
        expected = WebhookSigner.sign_payload(payload_bytes, secret)
        return hmac.compare_digest(expected, (signature_header or "").strip())
