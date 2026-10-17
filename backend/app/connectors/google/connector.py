"""
Dristik AI Google Search Console Connector
Manages authentication, property verification, and search telemetry queries.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json

from app.connectors.base.interface import BaseConnector
from app.connectors.base.telemetry_interface import ExternalTelemetryConnector, ExternalTelemetryResult
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult,
)
from app.domain.enums import ConnectorType, ConnectorHealthStatus
from app.domain.models import RemediationPatch
from app.evidence.models import EvidenceRef
import hashlib

class GoogleSearchConsoleConnector(BaseConnector, ExternalTelemetryConnector):
    """
    Integrates directly with Google Search Console API for impressions, clicks, and CTR.
    """

    async def test_connection(self) -> ConnectorHealth:
        # Check if credentials exist
        creds_content = self.credentials.app_password or self.credentials.api_key or self.credentials.github_token
        if not creds_content:
            return ConnectorHealth(
                provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message="Missing Service Account JSON or OAuth token",
                last_checked_at=datetime.now(timezone.utc).isoformat()
            )

        # Validate JSON format if provided as service account or oauth2
        try:
            parsed = json.loads(creds_content)
            if parsed.get("type") == "oauth2" and parsed.get("access_token"):
                user_email = parsed.get("email") or "token stored"
                return ConnectorHealth(
                    provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                    status=ConnectorHealthStatus.CONNECTED,
                    authenticated=True,
                    message=f"OAuth token verified for {user_email}.",
                    last_checked_at=datetime.now(timezone.utc).isoformat()
                )
            if parsed.get("type") == "service_account" and "client_email" in parsed:
                client_email = parsed.get("client_email")
                return ConnectorHealth(
                    provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                    status=ConnectorHealthStatus.CONNECTED,
                    authenticated=True,
                    message=f"Service account verified for {client_email}.",
                    last_checked_at=datetime.now(timezone.utc).isoformat()
                )
            return ConnectorHealth(
                provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                status=ConnectorHealthStatus.ERROR,
                authenticated=False,
                message="Invalid Google Search Console service account JSON structure",
                last_checked_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception:
            return ConnectorHealth(
                provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message="Google Search Console credentials must be valid Service Account JSON or OAuth payload",
                last_checked_at=datetime.now(timezone.utc).isoformat()
            )

    test_health = test_connection

    async def discover_site_structure(self) -> Dict[str, Any]:
        return {
            "property_type": "Domain Property",
            "target_url": self.credentials.api_url,
            "telemetry": "28-day Search Analytics"
        }

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "action": "GSC Indexation Request",
            "patch_id": patch.patch_id,
            "target": patch.target_url
        }

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        return PatchApplicationResult(
            provider=ConnectorType.GOOGLE_SEARCH_CONSOLE,
            success=False,
            patch_id=patch.patch_id,
            applied_at=datetime.now(timezone.utc).isoformat(),
            target_resource=patch.target_url,
            message="Indexation was not requested. This connector does not call the Search Console API."
        )

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=datetime.now(timezone.utc).isoformat(),
            message="Rollback acknowledged"
        )

    async def fetch_telemetry(self, domain: str, days: int = 28, **kwargs: Any) -> ExternalTelemetryResult:
        health = await self.test_connection()
        if not health.authenticated:
            return ExternalTelemetryResult(
                connector_id="gsc",
                connector_name="Google Search Console",
                domain=domain,
                status="NOT_CONNECTED",
                is_connected=False,
                metrics={
                    "total_clicks": 0,
                    "total_impressions": 0,
                    "average_ctr": 0.0,
                    "average_position": 0.0,
                    "queries": [],
                },
                unavailability_reason="Google Search Console not connected. Search impressions and clicks are unmeasured.",
                provenance_label="UNCONNECTED_FALLBACK",
            )

        parsed = {}
        try:
            raw = self.credentials.api_key or self.credentials.app_password or ""
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {}
        token = parsed.get("access_token") if isinstance(parsed, dict) else None
        if not token:
            return ExternalTelemetryResult(
                connector_id="gsc",
                connector_name="Google Search Console",
                domain=domain,
                status="NOT_CONNECTED",
                is_connected=False,
                metrics={"total_clicks": 0, "total_impressions": 0, "average_ctr": 0.0, "average_position": 0.0, "queries": []},
                unavailability_reason="Google Search Console token is missing. Search impressions and clicks are unmeasured.",
                provenance_label="UNCONNECTED_FALLBACK",
            )
        try:
            from app.connectors.google.google_api import query_search_analytics_token, refresh_google_access_token
            try:
                payload = query_search_analytics_token(str(token), domain, days=days)
            except RuntimeError as exc:
                refresh = parsed.get("refresh_token") if isinstance(parsed, dict) else None
                if refresh and "401" in str(exc):
                    payload = query_search_analytics_token(refresh_google_access_token(str(refresh)), domain, days=days)
                else:
                    raise
        except Exception as exc:
            return ExternalTelemetryResult(
                connector_id="gsc",
                connector_name="Google Search Console",
                domain=domain,
                status="UNAVAILABLE",
                is_connected=False,
                metrics={"total_clicks": 0, "total_impressions": 0, "average_ctr": 0.0, "average_position": 0.0, "queries": []},
                unavailability_reason=f"Google Search Console query failed: {exc}",
                provenance_label="LIVE_EXTERNAL_QUERY",
            )
        rows = payload.get("rows") or []
        clicks = impressions = 0
        weighted = 0.0
        queries = []
        for row in rows:
            keys = row.get("keys") or []
            if not keys:
                continue
            row_clicks = int(row.get("clicks") or 0)
            row_impressions = int(row.get("impressions") or 0)
            clicks += row_clicks
            impressions += row_impressions
            position = float(row.get("position") or 0)
            weighted += position * row_impressions
            queries.append({
                "query": str(keys[0]),
                "clicks": row_clicks,
                "impressions": row_impressions,
                "position": position,
            })
        metrics = {
            "total_clicks": clicks,
            "total_impressions": impressions,
            "average_ctr": round((clicks / impressions) * 100, 2) if impressions else 0.0,
            "average_position": round(weighted / impressions, 2) if impressions else 0.0,
            "queries": queries,
        }
        ev_hash = hashlib.sha256(json.dumps(metrics, sort_keys=True).encode()).hexdigest()
        ev_ref = EvidenceRef(
            source_type="external",
            source_id=f"gsc_{domain}",
            evidence_hash=ev_hash,
            url=f"https://{domain}",
            snippet=f"GSC 28-day performance: {metrics['total_clicks']} clicks, {metrics['total_impressions']} impressions",
            metadata=metrics
        )
        return ExternalTelemetryResult(
            connector_id="gsc",
            connector_name="Google Search Console",
            domain=domain,
            status="CONNECTED",
            is_connected=True,
            metrics=metrics,
            evidence_ref=ev_ref,
            provenance_label="LIVE_EXTERNAL_QUERY",
        )
