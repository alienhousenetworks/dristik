"""Phases 28 & 29 — GEO Provider Connector Manager, Secret Encryption & Privacy Governance.

Reuses Dristik's Fernet AES-128-CBC + HMAC credential encryption (`app.connectors.authority.crypto`)
so API keys are encrypted at rest and NEVER returned to the frontend. Also provides
deterministic PII redaction for prompts sent to external AI providers and health/capability inspection.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.connectors.authority.crypto import EncryptionKeyMissing, decrypt_json, encrypt_json
from app.db.geo_schema import GEOStore, get_geo_store
from app.geo.adapters.base import BaseGeoEngineAdapter
from app.geo.adapters.registry import (
    build_adapter_with_secret,
    get_adapter,
    get_all_adapters,
    get_provider_capability_matrix,
)
from app.geo.models import GEODataQualityState, GEOProviderConnection, GEOTestingMode

# Deterministic PII scrubbers for Phase 29 privacy governance
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\d)")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")

# Default per-tenant fallback encryption key derivation when EXTERNAL_INTEGRATION_ENCRYPTION_KEY
# is unset only in local/test mode (production should always set EXTERNAL_INTEGRATION_ENCRYPTION_KEY).
def _resolve_encryption_key() -> str:
    env_key = os.getenv("EXTERNAL_INTEGRATION_ENCRYPTION_KEY") or os.getenv("DRISTIK_SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    try:
        from app.core.config import settings
        for attr in ("EXTERNAL_INTEGRATION_ENCRYPTION_KEY", "SECRET_KEY", "JWT_SECRET_KEY"):
            val = getattr(settings, attr, None)
            if val and str(val).strip():
                return str(val).strip()
    except Exception:
        pass
    raise EncryptionKeyMissing(
        "EXTERNAL_INTEGRATION_ENCRYPTION_KEY is required to store encrypted GEO provider credentials."
    )


def redact_prompt_pii(prompt: str) -> Tuple[str, List[str]]:
    """Remove customer PII patterns before dispatching prompts to external AI APIs."""
    redacted = prompt or ""
    found: List[str] = []
    for label, pattern in (
        ("email", _EMAIL_RE),
        ("ssn", _SSN_RE),
        ("payment_card", _CARD_RE),
        ("phone", _PHONE_RE),
    ):
        if pattern.search(redacted):
            found.append(label)
            redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted, found


class GEOConnectorManager:
    """Manages encrypted per-tenant AI provider connections and dynamic capability matrices."""

    def __init__(self, store: Optional[GEOStore] = None):
        self.store = store or get_geo_store()

    def connect_provider(
        self,
        *,
        tenant_id: str,
        platform_id: str,
        api_key: str,
        model: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        testing_mode: Optional[GEOTestingMode] = None,
    ) -> GEOProviderConnection:
        pid = platform_id.lower().strip()
        key_material = _resolve_encryption_key()
        secret_payload = {"api_key": api_key.strip(), "endpoint_url": (endpoint_url or "").strip()}
        ciphertext = encrypt_json(secret_payload, key_material=key_material)

        adapter = build_adapter_with_secret(pid, api_key=api_key.strip(), model=model or "", endpoint_url=endpoint_url or "")
        if adapter is None:
            raise ValueError(f"Unsupported GEO platform '{platform_id}'.")

        caps = adapter.get_capabilities()
        conn = GEOProviderConnection(
            tenant_id=tenant_id,
            platform_id=adapter.engine_id,
            display_name=adapter.display_name,
            connected=True,
            auth_status="CONNECTED",
            default_model=adapter.model,
            testing_mode=testing_mode or adapter.default_testing_mode,
            capabilities=caps,
            last_successful_sync=datetime.now(timezone.utc).isoformat(),
            rate_limit_rpm=caps.rate_limit_rpm,
            data_freshness="live_on_demand",
            permissions=["prompt_execution"],
            cost_implication_note=(
                f"Est. ${caps.est_cost_per_1k_input_tokens_usd:.5f}/1k in · "
                f"${caps.est_cost_per_1k_output_tokens_usd:.5f}/1k out"
            ),
            has_stored_secret=True,
            data_quality_state=GEODataQualityState.OBSERVED,
        )
        return self.store.save_provider_connection(conn, encrypted_secret=ciphertext)

    def resolve_adapter_for_tenant(self, tenant_id: str, platform_id: str) -> Optional[BaseGeoEngineAdapter]:
        """Resolve a tenant's encrypted credential first, then fall back to global env adapter."""
        pid = platform_id.lower().strip()
        ciphertext = self.store.get_encrypted_provider_secret(tenant_id, pid)
        if ciphertext:
            try:
                secret = decrypt_json(ciphertext, key_material=_resolve_encryption_key())
                conns = {c.platform_id: c for c in self.store.list_provider_connections(tenant_id)}
                model = conns[pid].default_model if pid in conns else ""
                return build_adapter_with_secret(
                    pid,
                    api_key=secret.get("api_key", ""),
                    model=model,
                    endpoint_url=secret.get("endpoint_url", ""),
                )
            except Exception:
                return build_adapter_with_secret(pid, api_key="")
        return get_adapter(pid)

    def list_connections_status(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Return safe connection metadata for every supported platform (never exposing secrets)."""
        stored = {c.platform_id: c for c in self.store.list_provider_connections(tenant_id)}
        out: List[Dict[str, Any]] = []
        for adapter in get_all_adapters():
            pid = adapter.engine_id
            caps = adapter.get_capabilities()
            if pid in stored:
                rec = stored[pid].model_dump()
                rec["capabilities"] = caps.model_dump()
                rec["connected"] = True
                rec["auth_status"] = "CONNECTED"
                out.append(rec)
            else:
                env_connected = adapter.is_configured()
                out.append(
                    GEOProviderConnection(
                        tenant_id=tenant_id,
                        platform_id=pid,
                        display_name=adapter.display_name,
                        connected=env_connected,
                        auth_status="CONNECTED" if env_connected else "NOT_CONFIGURED",
                        default_model=adapter.model,
                        testing_mode=adapter.default_testing_mode,
                        capabilities=caps,
                        rate_limit_rpm=caps.rate_limit_rpm,
                        cost_implication_note=(
                            f"Est. ${caps.est_cost_per_1k_input_tokens_usd:.5f}/1k in · "
                            f"${caps.est_cost_per_1k_output_tokens_usd:.5f}/1k out"
                        ),
                        has_stored_secret=False,
                        data_quality_state=(
                            GEODataQualityState.OBSERVED if env_connected else GEODataQualityState.NOT_CONFIGURED
                        ),
                    ).model_dump()
                )
        return out

    def get_external_connector_summary(self) -> List[Dict[str, Any]]:
        """Expose status of supporting external data connectors (GSC, GA4, Bing, SERP, Reviews)."""
        env_checks = [
            ("gsc", "Google Search Console", bool(os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GSC_CREDENTIALS")), "Traditional organic search discovery context"),
            ("ga4", "Google Analytics 4", bool(os.getenv("GA4_PROPERTY_ID") or os.getenv("GOOGLE_CLIENT_ID")), "Downstream AI referral traffic & business impact"),
            ("bing_webmaster", "Bing Webmaster Tools", bool(os.getenv("BING_WEBMASTER_API_KEY")), "Bing/Copilot search index context"),
            ("serp_provider", "SERP & AI Overview Data", bool(os.getenv("SERPAPI_KEY") or os.getenv("DATAFORSEO_LOGIN")), "Search & SERP contextual signals"),
            ("review_sources", "Review & Reputation Discovery", bool(os.getenv("TRUSTPILOT_API_KEY") or os.getenv("G2_API_KEY")), "Independent public customer reviews"),
        ]
        return [
            {
                "connector_id": cid,
                "name": name,
                "connected": ok,
                "status": "CONNECTED" if ok else "NOT_CONFIGURED",
                "purpose": purpose,
                "note": "Read-only supporting context; missing connector is reported as NOT_CONFIGURED, never zero.",
            }
            for cid, name, ok, purpose in env_checks
        ]

    @staticmethod
    def capability_matrix() -> List[Dict[str, Any]]:
        return get_provider_capability_matrix()


geo_connector_manager = GEOConnectorManager()
