"""
Dristik AI DataForSEO Live SERP & Backlink Connector
Integrates with DataForSEO APIs to pull:
- Real keyword search volumes
- Live SERP competitor rankings
- Backlink graphs and referring domains
"""
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import base64
import httpx

from app.core.config import settings
from app.connectors.base.interface import BaseConnector
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult,
)
from app.domain.enums import ConnectorType, ConnectorHealthStatus
from app.domain.models import RemediationPatch


class DataForSeoConnector(BaseConnector):
    """
    Connects to DataForSEO live keyword and backlink APIs.
    """

    async def test_connection(self) -> ConnectorHealth:
        login = self.credentials.username or settings.DATAFORSEO_LOGIN or os.getenv("DATAFORSEO_LOGIN")
        password = self.credentials.app_password or self.credentials.api_key or settings.DATAFORSEO_PASSWORD or os.getenv("DATAFORSEO_PASSWORD")

        if not login or not password:
            return ConnectorHealth(
                provider=ConnectorType.DATAFORSEO,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message="Missing DataForSEO API Login / Password",
                last_checked_at=datetime.now(timezone.utc).isoformat(),
            )

        # Check live credentials against DataForSEO user endpoint
        try:
            auth_str = f"{login}:{password}"
            encoded_auth = base64.b64encode(auth_str.encode()).decode()
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://api.dataforseo.com/v3/appendix/user",
                    headers={"Authorization": f"Basic {encoded_auth}"},
                )
                if res.status_code == 200:
                    data = res.json()
                    balance = data.get("tasks", [{}])[0].get("result", [{}])[0].get("money", 0.0) if data.get("tasks") else 0.0
                    return ConnectorHealth(
                        provider=ConnectorType.DATAFORSEO,
                        status=ConnectorHealthStatus.CONNECTED,
                        authenticated=True,
                        message=f"DataForSEO connected. Active balance: ${balance:.2f}",
                        last_checked_at=datetime.now(timezone.utc).isoformat(),
                        permissions_granted=["serp_api", "backlinks_api", "keywords_data"],
                    )
        except Exception as e:
            return ConnectorHealth(
                provider=ConnectorType.DATAFORSEO,
                status=ConnectorHealthStatus.DISCONNECTED,
                authenticated=False,
                message=f"DataForSEO credentials configured but endpoint unreachable: {str(e)}",
                last_checked_at=datetime.now(timezone.utc).isoformat(),
            )

        return ConnectorHealth(
            provider=ConnectorType.DATAFORSEO,
            status=ConnectorHealthStatus.DISCONNECTED,
            authenticated=False,
            message="DataForSEO authentication rejected invalid login credentials.",
            last_checked_at=datetime.now(timezone.utc).isoformat(),
        )

    async def discover_site_structure(self) -> Dict[str, Any]:
        return {"endpoints": ["serp/google/organic", "backlinks/summary", "keywords_data/google/search_volume"]}

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {"status": "read_only_index"}

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        return PatchApplicationResult(
            patch_id=patch.patch_id,
            success=False,
            message="DataForSEO connector is read-only telemetry",
            applied_at=datetime.now(timezone.utc).isoformat(),
        )

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        return RollbackResult(
            patch_id=patch.patch_id,
            success=False,
            message="DataForSEO connector cannot be rolled back",
            rolled_back_at=datetime.now(timezone.utc).isoformat(),
        )
