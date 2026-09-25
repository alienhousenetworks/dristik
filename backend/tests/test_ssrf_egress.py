import pytest
from app.core.security.ssrf import is_safe_url

def test_ssrf_metadata_and_localhost_blocking():
    # AWS/GCP/Azure link-local metadata IPs
    safe, msg = is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert safe is False
    assert "Blocked target hostname" in msg or "restricted" in msg

    # Localhost and loopback
    safe, msg = is_safe_url("http://localhost:8000/admin")
    assert safe is False

    safe, msg = is_safe_url("http://127.0.0.1:3000")
    assert safe is False

    # Private internal IP ranges
    safe, msg = is_safe_url("http://10.0.1.50/internal")
    assert safe is False

    safe, msg = is_safe_url("http://192.168.1.1/router")
    assert safe is False

    # Valid public websites
    safe, msg = is_safe_url("https://linear.app")
    assert safe is True

    safe, msg = is_safe_url("https://supabase.com")
    assert safe is True

def test_tenant_egress_allowlist():
    allowlist = ["stripe.com", "api.stripe.com"]
    
    # Matching domain
    safe, msg = is_safe_url("https://stripe.com/docs", egress_allowlist=allowlist)
    assert safe is True

    safe, msg = is_safe_url("https://api.stripe.com/v1", egress_allowlist=allowlist)
    assert safe is True

    # Non-matching domain should be rejected
    safe, msg = is_safe_url("https://google.com", egress_allowlist=allowlist)
    assert safe is False
    assert "not in tenant egress allowlist" in msg
