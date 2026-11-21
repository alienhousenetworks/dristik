"""
Unified SEO Connectors & Integration Manager.
Stores tenant/workspace-scoped credentials encrypted at rest using Fernet (AES-128-CBC + HMAC)
inside the seo_connectors table, tracks live sync timestamps, data freshness, and API quotas.
Fail-closed epistemic discipline: zero synthetic metrics when unconnected.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.connectors.authority.crypto import EncryptionKeyMissing, decrypt_json, encrypt_json
from app.db.seo_orchestrator_schema import default_seo_db_path, init_seo_orchestrator_schema

logger = logging.getLogger(__name__)

# Process-local fallback encryption key ONLY when EXTERNAL_INTEGRATION_ENCRYPTION_KEY
# is not configured in local dev/unit tests (credentials are still encrypted, never plaintext).
_EPHEMERAL_FALLBACK_KEY: Optional[str] = None


def _resolve_encryption_key() -> str:
    global _EPHEMERAL_FALLBACK_KEY
    env_key = os.getenv("EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key
    try:
        from app.core.config import settings
        cfg_key = str(getattr(settings, "EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "") or "").strip()
        if cfg_key:
            return cfg_key
        if str(getattr(settings, "ENVIRONMENT", "development")).lower() == "production":
            raise EncryptionKeyMissing("EXTERNAL_INTEGRATION_ENCRYPTION_KEY is required in production.")
    except EncryptionKeyMissing:
        raise
    except Exception:
        pass
    if _EPHEMERAL_FALLBACK_KEY is None:
        from cryptography.fernet import Fernet
        _EPHEMERAL_FALLBACK_KEY = Fernet.generate_key().decode("ascii")
    return _EPHEMERAL_FALLBACK_KEY


class ConnectorStatus(BaseModel):
    provider_id: str
    label: str
    category: str
    status: str  # 'CONNECTED' | 'NOT_CONFIGURED' | 'ERROR' | 'QUOTA_EXCEEDED'
    scopes_granted: List[str] = Field(default_factory=list)
    scopes_required: List[str] = Field(default_factory=list)
    daily_quota_limit: int = 10000
    daily_quota_used: int = 0
    last_sync_timestamp: Optional[str] = None
    data_freshness_hours: Optional[float] = None
    health_message: str = ""
    workspace_id: str = "ws_default"


class ConnectorManager:
    """
    Durable, encrypted, tenant-scoped repository and health monitor for external SEO providers.
    """

    PROVIDERS: Dict[str, Dict[str, Any]] = {
        "google_search_console": {
            "label": "Google Search Console",
            "category": "Google Ecosystem",
            "scopes_required": ["https://www.googleapis.com/auth/webmasters.readonly"],
            "daily_quota_limit": 10000,
        },
        "google_analytics_4": {
            "label": "Google Analytics 4",
            "category": "Google Ecosystem",
            "scopes_required": ["https://www.googleapis.com/auth/analytics.readonly"],
            "daily_quota_limit": 25000,
        },
        "pagespeed_crux": {
            "label": "PageSpeed Insights & CrUX",
            "category": "Google Ecosystem",
            "scopes_required": ["https://www.googleapis.com/auth/pagespeedonline"],
            "daily_quota_limit": 25000,
        },
        "backlink_provider": {
            "label": "DataForSEO Backlink Intelligence",
            "category": "Authority & Backlinks",
            "scopes_required": ["api.dataforseo.com/v3/backlinks"],
            "daily_quota_limit": 50000,
        },
        "keyword_serp_provider": {
            "label": "DataForSEO SERP & Keywords",
            "category": "Search Performance",
            "scopes_required": ["api.dataforseo.com/v3/serp"],
            "daily_quota_limit": 50000,
        },
        "google_business_profile": {
            "label": "Google Business Profile",
            "category": "Local SEO",
            "scopes_required": ["https://www.googleapis.com/auth/business.manage"],
            "daily_quota_limit": 5000,
        },
        "bing_webmaster": {
            "label": "Bing Webmaster Tools",
            "category": "Multi-Engine Search",
            "scopes_required": ["webmasterapi.bing.com"],
            "daily_quota_limit": 10000,
        },
    }

    AGENT_TO_PROVIDER: Dict[str, str] = {
        "agent_search_console": "google_search_console",
        "agent_ga4_analytics": "google_analytics_4",
        "agent_technical_cwv": "pagespeed_crux",
        "agent_authority_backlinks": "backlink_provider",
        "agent_authority_referring_domains": "backlink_provider",
        "agent_keyword_serp": "keyword_serp_provider",
        "agent_competitor_seo": "keyword_serp_provider",
        "agent_local_gbp": "google_business_profile",
        "agent_bing_webmaster": "bing_webmaster",
    }

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or default_seo_db_path()
        init_seo_orchestrator_schema(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _compute_freshness_hours(ts: Optional[str]) -> Optional[float]:
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
            return round(max(0.0, delta), 2)
        except Exception:
            return None

    def get_connector_status(
        self,
        provider_id: str,
        workspace_id: str = "ws_default",
        org_id: Optional[str] = None,
    ) -> ConnectorStatus:
        meta = self.PROVIDERS.get(provider_id)
        if not meta:
            return ConnectorStatus(
                provider_id=provider_id,
                label=provider_id,
                category="Unknown",
                status="NOT_CONFIGURED",
                health_message="Provider ID not recognized.",
                workspace_id=workspace_id,
            )

        with self._connect() as conn:
            if org_id:
                row = conn.execute(
                    "SELECT * FROM seo_connectors WHERE workspace_id = ? AND connector_type = ? AND org_id = ?",
                    (workspace_id, provider_id, org_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM seo_connectors WHERE workspace_id = ? AND connector_type = ?",
                    (workspace_id, provider_id),
                ).fetchone()

        if row and row["status"] == "CONNECTED":
            scopes = []
            try:
                scopes = json.loads(row["scopes_json"] or "[]")
            except Exception:
                scopes = meta["scopes_required"]
            quota_used = int(row["daily_quota_used"] or 0)
            quota_limit = int(row["daily_quota_limit"] or meta["daily_quota_limit"])
            status_val = "QUOTA_EXCEEDED" if quota_used >= quota_limit else "CONNECTED"
            return ConnectorStatus(
                provider_id=provider_id,
                label=meta["label"],
                category=meta["category"],
                status=status_val,
                scopes_granted=scopes or meta["scopes_required"],
                scopes_required=meta["scopes_required"],
                daily_quota_limit=quota_limit,
                daily_quota_used=quota_used,
                last_sync_timestamp=row["last_synced_at"],
                data_freshness_hours=self._compute_freshness_hours(row["last_synced_at"]),
                health_message=row["health_message"] or "Active encrypted connection.",
                workspace_id=workspace_id,
            )

        return ConnectorStatus(
            provider_id=provider_id,
            label=meta["label"],
            category=meta["category"],
            status="NOT_CONFIGURED",
            scopes_granted=[],
            scopes_required=meta["scopes_required"],
            daily_quota_limit=meta["daily_quota_limit"],
            daily_quota_used=0,
            last_sync_timestamp=None,
            data_freshness_hours=None,
            health_message="Not configured. Connect OAuth or API credentials to stream live data.",
            workspace_id=workspace_id,
        )

    def list_all_connectors(
        self,
        workspace_id: str = "ws_default",
        org_id: Optional[str] = None,
    ) -> List[ConnectorStatus]:
        return [self.get_connector_status(pid, workspace_id=workspace_id, org_id=org_id) for pid in self.PROVIDERS]

    def connect_provider(
        self,
        provider_id: str,
        credentials: Dict[str, Any],
        *,
        workspace_id: str = "ws_default",
        org_id: str = "",
    ) -> ConnectorStatus:
        """Encrypts and persists credentials in seo_connectors after validating non-empty credentials."""
        if provider_id not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_id}")
        if not isinstance(credentials, dict) or not any(str(v).strip() for v in credentials.values() if v is not None):
            raise ValueError("Non-empty OAuth token or API key credentials are required.")

        meta = self.PROVIDERS[provider_id]
        key = _resolve_encryption_key()
        encrypted = encrypt_json(credentials, key_material=key)
        now_iso = datetime.now(timezone.utc).isoformat()
        scopes = credentials.get("scopes") if isinstance(credentials.get("scopes"), list) else meta["scopes_required"]

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT org_id FROM seo_connectors WHERE workspace_id = ? AND connector_type = ?",
                (workspace_id, provider_id),
            ).fetchone()
            if existing and existing["org_id"] and org_id and existing["org_id"] != org_id:
                raise PermissionError("Workspace connector belongs to another organization.")
            conn.execute(
                """
                INSERT INTO seo_connectors (
                    id, org_id, workspace_id, connector_type, status,
                    encrypted_credentials, scopes_json, daily_quota_limit,
                    daily_quota_used, health_message, last_synced_at, updated_at
                ) VALUES (?, ?, ?, ?, 'CONNECTED', ?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(workspace_id, connector_type) DO UPDATE SET
                    org_id = excluded.org_id,
                    status = 'CONNECTED',
                    encrypted_credentials = excluded.encrypted_credentials,
                    scopes_json = excluded.scopes_json,
                    health_message = excluded.health_message,
                    last_synced_at = excluded.last_synced_at,
                    updated_at = excluded.updated_at
                """,
                (
                    f"conn_{uuid.uuid4().hex[:12]}",
                    org_id,
                    workspace_id,
                    provider_id,
                    encrypted,
                    json.dumps(scopes),
                    meta["daily_quota_limit"],
                    "Encrypted credentials stored and validated.",
                    now_iso,
                    now_iso,
                ),
            )
            conn.commit()
        return self.get_connector_status(provider_id, workspace_id=workspace_id, org_id=org_id or None)

    def get_decrypted_credentials(
        self,
        provider_id: str,
        workspace_id: str = "ws_default",
        org_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            if org_id:
                row = conn.execute(
                    "SELECT encrypted_credentials FROM seo_connectors WHERE workspace_id = ? AND connector_type = ? AND org_id = ? AND status = 'CONNECTED'",
                    (workspace_id, provider_id, org_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT encrypted_credentials FROM seo_connectors WHERE workspace_id = ? AND connector_type = ? AND status = 'CONNECTED'",
                    (workspace_id, provider_id),
                ).fetchone()
        if not row or not row["encrypted_credentials"]:
            return None
        return decrypt_json(row["encrypted_credentials"], key_material=_resolve_encryption_key())

    def record_quota_use(self, provider_id: str, calls: int = 1, workspace_id: str = "ws_default") -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE seo_connectors
                SET daily_quota_used = daily_quota_used + ?, last_synced_at = ?, updated_at = ?
                WHERE workspace_id = ? AND connector_type = ?
                """,
                (max(0, int(calls)), now_iso, now_iso, workspace_id, provider_id),
            )
            conn.commit()

    def disconnect_provider(
        self,
        provider_id: str,
        workspace_id: str = "ws_default",
        org_id: Optional[str] = None,
    ) -> bool:
        with self._connect() as conn:
            if org_id:
                cur = conn.execute(
                    "DELETE FROM seo_connectors WHERE workspace_id = ? AND connector_type = ? AND org_id = ?",
                    (workspace_id, provider_id, org_id),
                )
            else:
                cur = conn.execute(
                    "DELETE FROM seo_connectors WHERE workspace_id = ? AND connector_type = ?",
                    (workspace_id, provider_id),
                )
            conn.commit()
            return cur.rowcount > 0

    def is_agent_connector_active(self, agent_id: str, workspace_id: str = "ws_default") -> bool:
        provider = self.AGENT_TO_PROVIDER.get(agent_id)
        if not provider:
            return True
        return self.get_connector_status(provider, workspace_id=workspace_id).status == "CONNECTED"


seo_connector_manager = ConnectorManager()
