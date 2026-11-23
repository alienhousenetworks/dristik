"""
Signed Outbound Webhook Publisher & Publish-to-Verification Audit Linker.

Adapted from GeoLook's MIT-licensed `scripts/publish.py` webhook bridge and
hardened for Dristik enterprise security:
- SSRF guard (`is_safe_url`)
- HMAC-SHA256 payload signature (`X-Dristik-Signature: sha256=<hex>`)
- Deterministic idempotency key (`X-Dristik-Idempotency-Key`)
- Explicit approval check (never publishes unapproved drafts)
- Links every published URL to its post-publish live verification record.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.security.ssrf import is_safe_url


class PublishedAssetRecord(BaseModel):
    publish_id: str = Field(default_factory=lambda: f"pub_{uuid.uuid4().hex[:12]}")
    tenant_id: str
    task_id: Optional[str] = None
    channel: str  # webhook | wordpress | github
    title: str
    idempotency_key: str
    approved_by: str
    published_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool
    published_url: str = ""
    http_status: Optional[int] = None
    verification_status: str = "PENDING_VERIFICATION"  # PENDING_VERIFICATION | VERIFIED_LIVE | VERIFICATION_FAILED
    verification_checked_at: Optional[str] = None
    error: str = ""


def sign_webhook_payload(raw_body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


async def publish_signed_webhook(
    *,
    webhook_url: str,
    webhook_secret: str,
    tenant_id: str,
    title: str,
    markdown: str,
    approved_by: str,
    task_id: Optional[str] = None,
    html: str = "",
    idempotency_key: Optional[str] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> PublishedAssetRecord:
    """POST a signed JSON payload to a configured outbound webhook and return an auditable record."""
    idem_key = idempotency_key or hashlib.sha256(f"{tenant_id}|{task_id or ''}|{title}".encode("utf-8")).hexdigest()[:24]

    if not approved_by or not approved_by.strip():
        return PublishedAssetRecord(
            tenant_id=tenant_id, task_id=task_id, channel="webhook", title=title,
            idempotency_key=idem_key, approved_by="", success=False,
            error="Explicit human approval (`approved_by`) is required before publishing.",
        )

    safe, reason = is_safe_url(webhook_url)
    if not safe:
        return PublishedAssetRecord(
            tenant_id=tenant_id, task_id=task_id, channel="webhook", title=title,
            idempotency_key=idem_key, approved_by=approved_by, success=False,
            error=f"Webhook blocked by SSRF guard: {reason}",
        )

    payload_obj: Dict[str, Any] = {
        "tenant_id": tenant_id,
        "task_id": task_id,
        "title": title,
        "markdown": markdown,
        "html": html,
        "approved_by": approved_by,
        "idempotency_key": idem_key,
    }
    raw_body = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Dristik-Idempotency-Key": idem_key,
        "X-Dristik-Signature": sign_webhook_payload(raw_body, webhook_secret),
    }

    try:
        if http_client is not None:
            resp = await http_client.post(webhook_url, content=raw_body, headers=headers, timeout=20.0)
        else:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(webhook_url, content=raw_body, headers=headers)

        if 200 <= resp.status_code < 300:
            pub_url = ""
            try:
                pub_url = str((resp.json() or {}).get("url") or "")
            except Exception:
                pub_url = ""
            return PublishedAssetRecord(
                tenant_id=tenant_id, task_id=task_id, channel="webhook", title=title,
                idempotency_key=idem_key, approved_by=approved_by, success=True,
                published_url=pub_url, http_status=resp.status_code,
            )
        return PublishedAssetRecord(
            tenant_id=tenant_id, task_id=task_id, channel="webhook", title=title,
            idempotency_key=idem_key, approved_by=approved_by, success=False,
            http_status=resp.status_code, error=f"HTTP {resp.status_code}: {resp.text[:200]}",
        )
    except Exception as exc:
        return PublishedAssetRecord(
            tenant_id=tenant_id, task_id=task_id, channel="webhook", title=title,
            idempotency_key=idem_key, approved_by=approved_by, success=False,
            error=f"Webhook delivery failed: {exc}",
        )


async def verify_published_asset(
    record: PublishedAssetRecord,
    *,
    http_client: Optional[httpx.AsyncClient] = None,
) -> PublishedAssetRecord:
    """Independently re-fetch `record.published_url` (SSRF-guarded) and link verification result."""
    record.verification_checked_at = datetime.now(timezone.utc).isoformat()
    if not record.success or not record.published_url:
        record.verification_status = "VERIFICATION_FAILED"
        return record
    safe, reason = is_safe_url(record.published_url)
    if not safe:
        record.verification_status = "VERIFICATION_FAILED"
        record.error = f"Verification URL blocked by SSRF guard: {reason}"
        return record
    try:
        if http_client is not None:
            resp = await http_client.get(record.published_url, timeout=10.0)
        else:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(record.published_url)
        record.verification_status = "VERIFIED_LIVE" if resp.status_code == 200 else "VERIFICATION_FAILED"
        if resp.status_code != 200:
            record.error = f"Published URL returned HTTP {resp.status_code}"
    except Exception as exc:
        record.verification_status = "VERIFICATION_FAILED"
        record.error = f"Verification fetch failed: {exc}"
    return record
