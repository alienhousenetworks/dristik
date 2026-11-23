"""
Enterprise Privacy, Security, Consent, DSAR, RBAC, Webhook & Rate-Limit Governance.

Implements:
- CMP consent recording & consent withdrawal propagation.
- Automated retention TTL purge policies.
- Tenant-isolated DSAR data export & right-to-erasure workflows.
- RBAC permission enforcement for recordings, analytics, disavow, and experiment rollouts.
- Encryption at rest & zero-downtime key rotation (Fernet / AES-128-CBC + HMAC-SHA256).
- Webhook HMAC-SHA256 signature + replay-window validation (Shopify, Stripe, WooCommerce, etc.).
- Per-tenant/IP token-bucket ingestion rate limiting & payload-size guard.
- Defense-in-depth server-side PII scrubbing (passwords, payment cards, emails, phone numbers).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from cryptography.fernet import Fernet, MultiFernet

from app.db.enterprise_intelligence_schema import connect_enterprise_db
from app.governance.data_reliability import utc_now_iso

ROLE_PERMISSIONS: Dict[str, set[str]] = {
    "owner": {
        "analytics:read", "replay:view", "experiments:approve_rollout",
        "disavow:approve", "privacy:dsar_admin", "ops:dlq_replay", "connectors:manage",
    },
    "admin": {
        "analytics:read", "replay:view", "experiments:approve_rollout",
        "disavow:approve", "privacy:dsar_admin", "ops:dlq_replay", "connectors:manage",
    },
    "analyst": {"analytics:read", "replay:view"},
    "developer": {"analytics:read", "ops:dlq_replay"},
    "viewer": {"analytics:read"},
}

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4})(?!\d)")
_SENSITIVE_KEY_RE = re.compile(r"(pass|pwd|card|cvv|cvc|ssn|aadhaar|pan|token|secret|auth)", re.IGNORECASE)


def check_rbac_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get((role or "viewer").strip().lower(), set())


def require_rbac_permission(role: str, permission: str) -> None:
    if not check_rbac_permission(role, permission):
        raise PermissionError(f"Role '{role}' lacks required permission '{permission}'.")


def scrub_pii_string(text: str) -> str:
    if not text:
        return text
    cleaned = _CARD_RE.sub("[MASKED_CARD]", text)
    cleaned = _EMAIL_RE.sub("[MASKED_EMAIL]", cleaned)
    cleaned = _PHONE_RE.sub("[MASKED_PHONE]", cleaned)
    return cleaned


def sanitize_behavioral_payload(payload: Any) -> Any:
    """Defense-in-depth PII masking for any incoming behavioral/replay/event payload."""
    if isinstance(payload, dict):
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            if _SENSITIVE_KEY_RE.search(str(k)):
                out[k] = "[MASKED_SENSITIVE]"
            else:
                out[k] = sanitize_behavioral_payload(v)
        return out
    if isinstance(payload, list):
        return [sanitize_behavioral_payload(item) for item in payload]
    if isinstance(payload, str):
        return scrub_pii_string(payload)
    return payload


class SecretVault:
    """Fernet-based credential encryption at rest with zero-downtime key rotation."""

    def __init__(self, primary_key: str, previous_keys: Optional[List[str]] = None):
        keys = [primary_key] + list(previous_keys or [])
        self._fernet = MultiFernet([Fernet(k.encode("utf-8") if isinstance(k, str) else k) for k in keys])

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    def rotate_token(self, ciphertext: str) -> str:
        return self._fernet.rotate(ciphertext.encode("utf-8")).decode("utf-8")


def verify_webhook_signature(
    *,
    secret: str,
    payload_bytes: bytes,
    signature_header: str,
    encoding: str = "hex",  # "hex" | "base64" | "stripe"
    timestamp_unix: Optional[int] = None,
    max_skew_seconds: int = 300,
    now_unix: Optional[int] = None,
) -> Tuple[bool, str]:
    """Constant-time HMAC-SHA256 webhook verification with replay-window check."""
    if not secret or not signature_header:
        return False, "Missing secret or signature header."
    now = int(now_unix if now_unix is not None else time.time())
    if timestamp_unix is not None and abs(now - int(timestamp_unix)) > max_skew_seconds:
        return False, "Webhook timestamp outside allowed replay window."

    if encoding == "stripe":
        parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
        ts_str = parts.get("t")
        v1 = parts.get("v1")
        if not ts_str or not v1:
            return False, "Malformed Stripe signature header."
        if abs(now - int(ts_str)) > max_skew_seconds:
            return False, "Stripe webhook timestamp expired."
        signed_payload = f"{ts_str}.".encode("utf-8") + payload_bytes
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        return (True, "OK") if hmac.compare_digest(expected, v1) else (False, "Invalid Stripe signature.")

    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if encoding == "base64":
        expected = base64.b64encode(digest).decode("utf-8")
    else:
        expected = digest.hex()
    provided = signature_header.replace("sha256=", "").strip()
    return (True, "OK") if hmac.compare_digest(expected, provided) else (False, "Invalid HMAC signature.")


class IngestionRateLimiter:
    """In-memory token-bucket rate limiter per (org_id, client_ip) + payload size cap."""

    def __init__(self, max_requests_per_min: int = 600, max_payload_bytes: int = 262144):
        self.max_requests_per_min = max(1, max_requests_per_min)
        self.max_payload_bytes = max(1024, max_payload_bytes)
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def allow(self, key: str, payload_bytes: int = 0, now: Optional[float] = None) -> Tuple[bool, str]:
        if payload_bytes > self.max_payload_bytes:
            return False, f"Payload exceeds {self.max_payload_bytes} bytes limit."
        t = now if now is not None else time.monotonic()
        rate_per_sec = self.max_requests_per_min / 60.0
        tokens, last_t = self._buckets.get(key, (float(self.max_requests_per_min), t))
        tokens = min(float(self.max_requests_per_min), tokens + (t - last_t) * rate_per_sec)
        if tokens < 1.0:
            self._buckets[key] = (tokens, t)
            return False, "Rate limit exceeded."
        self._buckets[key] = (tokens - 1.0, t)
        return True, "OK"


class PrivacyGovernanceService:
    """Tenant-isolated CMP consent, retention TTL purge, and DSAR export/erasure."""

    @classmethod
    def record_consent(
        cls,
        *,
        org_id: str,
        subject_id: str,
        analytics_granted: bool,
        replay_granted: bool,
        experimentation_granted: bool,
        cmp_provider: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        cid = f"cns_{uuid.uuid4().hex[:12]}"
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO consent_records (
                    consent_id, org_id, subject_id, analytics_granted, replay_granted,
                    experimentation_granted, cmp_provider, status, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
                ON CONFLICT(org_id, subject_id) DO UPDATE SET
                    analytics_granted=excluded.analytics_granted,
                    replay_granted=excluded.replay_granted,
                    experimentation_granted=excluded.experimentation_granted,
                    cmp_provider=excluded.cmp_provider,
                    status='ACTIVE',
                    updated_at_utc=excluded.updated_at_utc
                """,
                (cid, org_id, subject_id, int(analytics_granted), int(replay_granted), int(experimentation_granted), cmp_provider, now),
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "org_id": org_id,
            "subject_id": subject_id,
            "analytics_granted": analytics_granted,
            "replay_granted": replay_granted,
            "experimentation_granted": experimentation_granted,
            "status": "ACTIVE",
        }

    @classmethod
    def withdraw_consent(
        cls,
        *,
        org_id: str,
        subject_id: str,
        requested_by: str = "subject",
        erase_existing: bool = True,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                UPDATE consent_records
                SET analytics_granted=0, replay_granted=0, experimentation_granted=0,
                    status='WITHDRAWN', updated_at_utc=?
                WHERE org_id = ? AND subject_id = ?
                """,
                (now, org_id, subject_id),
            )
            conn.commit()
        finally:
            conn.close()
        erased = cls.delete_subject_data(org_id=org_id, subject_id=subject_id, requested_by=requested_by, db_path=db_path) if erase_existing else {"records_deleted": 0}
        return {"org_id": org_id, "subject_id": subject_id, "status": "WITHDRAWN", **erased}

    @classmethod
    def check_consent(cls, *, org_id: str, subject_id: str, category: str = "analytics", db_path: Optional[str] = None) -> bool:
        col_map = {
            "analytics": "analytics_granted",
            "replay": "replay_granted",
            "experimentation": "experimentation_granted",
        }
        col = col_map.get(category)
        if not col:
            return False
        conn = connect_enterprise_db(db_path)
        try:
            row = conn.execute(
                f"SELECT {col}, status FROM consent_records WHERE org_id = ? AND subject_id = ?",
                (org_id, subject_id),
            ).fetchone()
            if not row:
                return False
            return row["status"] == "ACTIVE" and bool(row[col])
        finally:
            conn.close()

    @classmethod
    def export_subject_data(
        cls, *, org_id: str, subject_id: str, requested_by: str, db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            sessions = [dict(r) for r in conn.execute("SELECT * FROM visitor_sessions WHERE org_id = ? AND visitor_id = ?", (org_id, subject_id)).fetchall()]
            events = [dict(r) for r in conn.execute("SELECT * FROM analytics_events WHERE org_id = ? AND visitor_id = ?", (org_id, subject_id)).fetchall()]
            conversions = [dict(r) for r in conn.execute("SELECT * FROM conversion_events WHERE org_id = ? AND visitor_id = ?", (org_id, subject_id)).fetchall()]
            total = len(sessions) + len(events) + len(conversions)
            req_id = f"dsar_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO dsar_requests (request_id, org_id, subject_id, request_type, status, requested_by, records_affected, created_at_utc, completed_at_utc)
                VALUES (?, ?, ?, 'EXPORT', 'COMPLETED', ?, ?, ?, ?)
                """,
                (req_id, org_id, subject_id, requested_by, total, now, now),
            )
            conn.commit()
            return {
                "request_id": req_id,
                "org_id": org_id,
                "subject_id": subject_id,
                "records_exported": total,
                "sessions": sessions,
                "events": events,
                "conversions": conversions,
            }
        finally:
            conn.close()

    @classmethod
    def delete_subject_data(
        cls, *, org_id: str, subject_id: str, requested_by: str, db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        now = utc_now_iso()
        conn = connect_enterprise_db(db_path)
        try:
            deleted = 0
            for table, col in (
                ("analytics_events", "visitor_id"),
                ("visitor_sessions", "visitor_id"),
                ("attribution_touchpoints", "visitor_id"),
                ("conversion_events", "visitor_id"),
                ("conversion_sessions", "visitor_id"),
            ):
                cur = conn.execute(f"DELETE FROM {table} WHERE org_id = ? AND {col} = ?", (org_id, subject_id))
                deleted += cur.rowcount
            req_id = f"dsar_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO dsar_requests (request_id, org_id, subject_id, request_type, status, requested_by, records_affected, created_at_utc, completed_at_utc)
                VALUES (?, ?, ?, 'ERASURE', 'COMPLETED', ?, ?, ?, ?)
                """,
                (req_id, org_id, subject_id, requested_by, deleted, now, now),
            )
            conn.commit()
            return {"request_id": req_id, "records_deleted": deleted}
        finally:
            conn.close()

    @classmethod
    def purge_expired_data(
        cls, *, org_id: str, retention_days: int = 90, now_utc: Optional[datetime] = None, db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        cutoff = ((now_utc or datetime.now(timezone.utc)) - timedelta(days=max(1, retention_days))).isoformat()
        conn = connect_enterprise_db(db_path)
        try:
            purged = 0
            for table, ts_col in (
                ("analytics_events", "event_ts_utc"),
                ("visitor_sessions", "started_at_utc"),
                ("attribution_touchpoints", "touchpoint_ts_utc"),
            ):
                cur = conn.execute(f"DELETE FROM {table} WHERE org_id = ? AND {ts_col} < ?", (org_id, cutoff))
                purged += cur.rowcount
            conn.commit()
            return {"org_id": org_id, "cutoff_utc": cutoff, "records_purged": purged}
        finally:
            conn.close()
