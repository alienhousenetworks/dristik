"""SSRF guard used before the crawler fetches a URL."""
from app.core.security.ssrf import BLOCKED_HOSTNAMES, BLOCKED_IP_NETWORKS, is_safe_url

__all__ = ["BLOCKED_HOSTNAMES", "BLOCKED_IP_NETWORKS", "is_safe_url"]
