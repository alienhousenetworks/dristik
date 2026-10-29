"""SSRF guard, content trust boundary, and enterprise audit log.

Customer sessions are opaque cookies. Token helpers live in app.identity.jwt.
"""
from app.core.security.ssrf import is_safe_url

__all__ = ["is_safe_url"]

