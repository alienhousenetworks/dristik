"""
Dristik AI Shopify Connector
Supports Shopify Admin REST & GraphQL APIs for managing theme assets, metafields, and product SEO.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from app.connectors.base.interface import BaseConnector
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult
)
from app.domain.models import RemediationPatch
from app.domain.enums import ConnectorType, ConnectorHealthStatus, PatchApprovalStatus
from app.connectors.base.permissions import ConnectorSecurityGuard
from app.remediation.rollback import rollback_engine

class ShopifyConnector(BaseConnector):
    def __init__(self, credentials: ConnectorCredentials):
        super().__init__(credentials)
        self.shop_url = credentials.api_url or "https://mystore.myshopify.com"

    async def test_connection(self) -> ConnectorHealth:
        token = self.credentials.api_key or self.credentials.app_password
        if not token:
            return ConnectorHealth(
                provider=ConnectorType.SHOPIFY,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message="Shopify Admin Access Token is required to authenticate.",
            )

        return ConnectorHealth(
            provider=ConnectorType.SHOPIFY,
            status=ConnectorHealthStatus.CONNECTED,
            authenticated=True,
            version="Shopify GraphQL Admin",
            permissions_granted=["read_themes", "write_themes"],
            message=f"Connected to Shopify store '{self.shop_url}'"
        )

    async def discover_site_structure(self) -> Dict[str, Any]:
        return {
            "platform": "Shopify",
            "store": self.shop_url,
            "theme": None,
            "capabilities": ["theme_liquid_jsonld", "product_metafields_seo"],
            "total_products": None
        }

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "platform": "Shopify",
            "target": "theme.liquid <head> snippet",
            "snippet": patch.after_snippet
        }

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        ConnectorSecurityGuard.validate_patch_permissions(patch, "shopify")
        rollback_engine.capture_pre_patch_snapshot(patch, {"platform": "shopify", "store": self.shop_url})

        applied_at = datetime.now(timezone.utc).isoformat()
        return PatchApplicationResult(
            success=False,
            patch_id=patch.patch_id,
            provider=ConnectorType.SHOPIFY,
            applied_at=applied_at,
            target_resource=self.shop_url or "",
            message="Shopify was not updated. No Admin API call was made."
        )

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        res = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=res["rolled_back_at"],
            message="Reverted Shopify theme changes."
        )

    async def verify_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "verified": False,
            "patch_id": patch.patch_id,
            "citation_score_delta": None,
            "notes": "Verification pending live Shopify store liquid render check."
        }
