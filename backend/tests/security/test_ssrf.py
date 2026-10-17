"""Fetch targets in loopback and link-local space are refused."""
from app.core.ssrf import is_safe_url


def test_loopback_and_metadata_addresses_are_blocked():
    for target in (
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/admin",
        "file:///etc/passwd",
    ):
        allowed, _reason = is_safe_url(target)
        assert allowed is False
