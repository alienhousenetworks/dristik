"""Tests for Phase 3: Privacy, Consent Withdrawal, DSAR, Retention, RBAC, Webhooks, Rate Limit & PII Masking."""
import hashlib
import hmac
import time
import pytest

from app.analytics.ai_referral_engine import AiReferralEngine
from app.security.privacy_governance import (
    IngestionRateLimiter,
    PrivacyGovernanceService,
    SecretVault,
    require_rbac_permission,
    sanitize_behavioral_payload,
    verify_webhook_signature,
)


def test_consent_withdrawal_dsar_and_tenant_isolation(tmp_path):
    db = str(tmp_path / "privacy.db")
    PrivacyGovernanceService.record_consent(
        org_id="org_a", subject_id="v_1", analytics_granted=True, replay_granted=True, experimentation_granted=True, db_path=db
    )
    assert PrivacyGovernanceService.check_consent(org_id="org_a", subject_id="v_1", category="replay", db_path=db) is True

    AiReferralEngine.record_session(
        org_id="org_a", domain="perforacare.com", session_id="s_a1", visitor_id="v_1",
        landing_page="/p", http_referrer="https://chatgpt.com/", started_at_utc="2025-01-01T00:00:00Z", db_path=db,
    )
    AiReferralEngine.record_session(
        org_id="org_b", domain="other.com", session_id="s_b1", visitor_id="v_1",
        landing_page="/p", http_referrer="https://chatgpt.com/", started_at_utc="2026-11-20T00:00:00Z", db_path=db,
    )

    # Tenant isolation: org_b exporting v_1 must NOT see org_a's session
    exp_b = PrivacyGovernanceService.export_subject_data(org_id="org_b", subject_id="v_1", requested_by="admin_b", db_path=db)
    assert exp_b["records_exported"] == 1
    assert exp_b["sessions"][0]["session_id"] == "s_b1"

    # Consent withdrawal in org_a erases org_a's records and leaves org_b untouched
    w = PrivacyGovernanceService.withdraw_consent(org_id="org_a", subject_id="v_1", erase_existing=True, db_path=db)
    assert w["status"] == "WITHDRAWN"
    assert w["records_deleted"] >= 1
    assert PrivacyGovernanceService.check_consent(org_id="org_a", subject_id="v_1", category="analytics", db_path=db) is False
    exp_b_after = PrivacyGovernanceService.export_subject_data(org_id="org_b", subject_id="v_1", requested_by="admin_b", db_path=db)
    assert exp_b_after["records_exported"] == 1


def test_retention_purge_rbac_vault_webhooks_rate_limit_and_pii_masking(tmp_path):
    db = str(tmp_path / "retention.db")
    AiReferralEngine.record_session(
        org_id="org_a", domain="perforacare.com", session_id="s_old", visitor_id="v_old",
        landing_page="/old", started_at_utc="2024-01-01T00:00:00Z", db_path=db,
    )
    purged = PrivacyGovernanceService.purge_expired_data(org_id="org_a", retention_days=90, db_path=db)
    assert purged["records_purged"] >= 1

    # RBAC
    require_rbac_permission("admin", "experiments:approve_rollout")
    with pytest.raises(PermissionError):
        require_rbac_permission("viewer", "replay:view")
    with pytest.raises(PermissionError):
        require_rbac_permission("analyst", "experiments:approve_rollout")

    # Secret encryption & zero-downtime key rotation
    k1 = SecretVault.generate_key()
    k2 = SecretVault.generate_key()
    v1 = SecretVault(k1)
    ct = v1.encrypt("super_secret_api_key")
    v2 = SecretVault(k2, previous_keys=[k1])
    assert v2.decrypt(ct) == "super_secret_api_key"
    rotated = v2.rotate_token(ct)
    assert SecretVault(k2).decrypt(rotated) == "super_secret_api_key"

    # Webhook HMAC verification + replay protection
    body = b'{"order_id":"ORD-1"}'
    sig = hmac.new(b"whsec_123", body, hashlib.sha256).hexdigest()
    now = int(time.time())
    assert verify_webhook_signature(secret="whsec_123", payload_bytes=body, signature_header=f"sha256={sig}", timestamp_unix=now, now_unix=now)[0] is True
    assert verify_webhook_signature(secret="whsec_123", payload_bytes=body, signature_header="bad", timestamp_unix=now, now_unix=now)[0] is False
    assert verify_webhook_signature(secret="whsec_123", payload_bytes=body, signature_header=sig, timestamp_unix=now - 600, now_unix=now)[0] is False

    # Rate limiting & payload size cap
    rl = IngestionRateLimiter(max_requests_per_min=2, max_payload_bytes=2048)
    assert rl.allow("org_a:1.2.3.4", payload_bytes=100, now=10.0)[0] is True
    assert rl.allow("org_a:1.2.3.4", payload_bytes=100, now=10.0)[0] is True
    assert rl.allow("org_a:1.2.3.4", payload_bytes=100, now=10.0)[0] is False
    assert rl.allow("org_a:1.2.3.5", payload_bytes=5000, now=10.0)[0] is False

    # PII scrubbing
    dirty = {"password": "mySecretPassword!", "note": "Contact user@example.com or 4111-1111-1111-1111"}
    clean = sanitize_behavioral_payload(dirty)
    assert clean["password"] == "[MASKED_SENSITIVE]"
    assert "user@example.com" not in clean["note"]
    assert "4111" not in clean["note"]
