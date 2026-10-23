"""Matrix 360 Consulting — DNS-Aware SSRF Protection, Robots.txt Guard, and Politeness Engine.

Guarantees:
1. DNS-level validation against private/loopback/cloud-metadata IPs (RFC1918, RFC4193, 169.254.x.x, 127.x.x.x).
2. Redirect control: prevents redirect hops to internal or unauthorized IPs.
3. Robots.txt checking: respects Disallow directives per domain.
4. Per-domain rate limiting to ensure polite, non-abusive crawling.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
import threading
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import Dict, Optional, Set, Tuple

logger = logging.getLogger("matrix360.security")

DIRECTORY_AND_SOCIAL_DOMAINS: Set[str] = {
    "indiamart.com",
    "justdial.com",
    "zaubacorp.com",
    "tofler.in",
    "tradeindia.com",
    "exportersindia.com",
    "facebook.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "pinterest.com",
    "wikipedia.org",
    "google.com",
    "yahoo.com",
    "duckduckgo.com",
    "bing.com",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / Cloud Metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),     # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),     # Documentation (TEST-NET-1)
    ipaddress.ip_network("198.51.100.0/24"),  # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),   # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IP string belongs to any private, loopback, or reserved range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return True
        return False
    except ValueError:
        return True


def validate_target_url(
    url: str,
    allow_private_for_tests: bool = False,
    allowed_ports: Optional[Set[int]] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a target URL for DNS SSRF safety, scheme, and directory exclusions.

    Returns: (is_safe, error_reason, resolved_ip)
    """
    if allowed_ports is None:
        allowed_ports = {80, 443, 8080, 8443}

    raw = (url or "").strip()
    if not raw:
        return False, "EMPTY_URL", None

    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw

    try:
        parsed = urllib.parse.urlparse(raw)
    except Exception as exc:
        return False, f"MALFORMED_URL: {exc}", None

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"UNSUPPORTED_SCHEME: {parsed.scheme}", None

    hostname = (parsed.hostname or "").lower().strip(".")
    if not hostname:
        return False, "INVALID_HOSTNAME", None

    # Check raw IP address FIRST before checking port or domain rules
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if not allow_private_for_tests and is_ip_private_or_restricted(str(ip_obj)):
            return False, f"SSRF_PROTECTED_PRIVATE_IP: {hostname}", str(ip_obj)
        if not allow_private_for_tests:
            return False, "RAW_IP_TARGET_DISALLOWED", str(ip_obj)
        return True, None, str(ip_obj)
    except ValueError:
        pass  # It's a domain name, proceed to DNS resolution check

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    if port not in allowed_ports and not allow_private_for_tests:
        return False, f"NON_STANDARD_PORT_DISALLOWED: {port}", None

    # Check third-party portal & social directory exclusions
    clean_host = hostname[4:] if hostname.startswith("www.") else hostname
    for bad in DIRECTORY_AND_SOCIAL_DOMAINS:
        if clean_host == bad or clean_host.endswith("." + bad):
            return False, f"THIRD_PARTY_DIRECTORY_OR_PORTAL: {bad}", None

    if allow_private_for_tests:
        return True, None, "127.0.0.1"

    # DNS-Aware SSRF Check: resolve domain and verify all resolved IPs
    try:
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        resolved_ips = set()
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            resolved_ips.add(ip_str)
            if is_ip_private_or_restricted(ip_str):
                return False, f"SSRF_DNS_RESOLVES_TO_PRIVATE_IP: {hostname} -> {ip_str}", ip_str
        primary_ip = next(iter(resolved_ips), None)
        return True, None, primary_ip
    except socket.gaierror as exc:
        return False, f"DNS_RESOLUTION_FAILED: {exc}", None
    except Exception as exc:
        return False, f"DNS_CHECK_ERROR: {exc}", None


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom HTTP redirect handler ensuring redirect hops do not point to SSRF targets."""

    def __init__(self, allow_private_for_tests: bool = False):
        super().__init__()
        self.allow_private_for_tests = allow_private_for_tests

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        is_safe, reason, _ = validate_target_url(
            newurl, allow_private_for_tests=self.allow_private_for_tests
        )
        if not is_safe:
            raise urllib.request.HTTPError(
                newurl, 403, f"SSRF_REDIRECT_BLOCKED: {reason}", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RobotsTxtGuard:
    """Thread-safe Robots.txt parser and cache for polite web crawling."""

    def __init__(self, user_agent: str = "Matrix360Bot"):
        self.user_agent = user_agent
        self._cache: Dict[str, Tuple[urllib.robotparser.RobotFileParser, float]] = {}
        self._lock = threading.Lock()
        self.cache_ttl_seconds = 3600  # 1 hour

    def can_fetch(self, url: str, allow_private_for_tests: bool = False) -> bool:
        parsed = urllib.parse.urlparse(url)
        root_domain = (parsed.netloc or parsed.hostname or "").lower()
        if not root_domain:
            return False

        now = time.time()
        with self._lock:
            cached = self._cache.get(root_domain)
            if cached and (now - cached[1]) < self.cache_ttl_seconds:
                rp = cached[0]
                return rp.can_fetch(self.user_agent, url)

        # Fetch and parse robots.txt
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)

        try:
            req = urllib.request.Request(
                robots_url,
                headers={"User-Agent": self.user_agent, "Accept": "text/plain"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    lines = resp.read().decode("utf-8", errors="ignore").splitlines()
                    rp.parse(lines)
                else:
                    rp.allow_all = True
        except Exception:
            # If robots.txt fails or 404s, standard crawler behavior is to allow
            rp.allow_all = True

        with self._lock:
            self._cache[root_domain] = (rp, now)

        return rp.can_fetch(self.user_agent, url)


class DomainRateLimiter:
    """Thread-safe per-domain rate limiter to avoid hammering websites."""

    def __init__(self, min_delay_seconds: float = 0.3):
        self.min_delay_seconds = min_delay_seconds
        self._last_request: Dict[str, float] = {}
        self._lock = threading.Lock()

    def wait_for_domain(self, domain: str) -> None:
        clean_dom = domain.lower().strip()
        with self._lock:
            now = time.time()
            last = self._last_request.get(clean_dom, 0.0)
            elapsed = now - last
            if elapsed < self.min_delay_seconds:
                sleep_time = self.min_delay_seconds - elapsed
            else:
                sleep_time = 0.0
            self._last_request[clean_dom] = now + sleep_time

        if sleep_time > 0:
            time.sleep(sleep_time)
