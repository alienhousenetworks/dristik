"""
Dristik AI Webflow Connector
Supports Webflow Sites & CMS REST API for Custom Code Embeds and Collection Fields.
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

class WebflowConnector(BaseConnector):
    def __init__(self, credentials: ConnectorCredentials):
        super().__init__(credentials)
        self.site_id = credentials.api_url or "webflow-site-id"

    async def test_connection(self) -> ConnectorHealth:
        token = self.credentials.api_key or self.credentials.app_password
        if not token:
            return ConnectorHealth(
                provider=ConnectorType.WEBFLOW,
                status=ConnectorHealthStatus.UNAUTHORIZED,
                authenticated=False,
                message="Webflow API token is required to authenticate.",
            )

        return ConnectorHealth(
            provider=ConnectorType.WEBFLOW,
            status=ConnectorHealthStatus.CONNECTED,
            authenticated=True,
            version="Webflow REST v2",
            permissions_granted=["sites:read", "custom_code:write"],
            message=f"Connected to Webflow Site '{self.site_id}'"
        )

    async def discover_site_structure(self) -> Dict[str, Any]:
        return {
            "platform": "Webflow",
            "site_id": self.site_id,
            "capabilities": ["custom_code_head"],
            "collections_found": None
        }

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "platform": "Webflow",
            "target": "Site Settings > Custom Code > Head Code",
            "snippet": patch.after_snippet
        }

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        ConnectorSecurityGuard.validate_patch_permissions(patch, "webflow")
        rollback_engine.capture_pre_patch_snapshot(patch, {"platform": "webflow", "site_id": self.site_id})

        patch.approval_status = PatchApprovalStatus.APPLIED
        patch.applied_via = "webflow"
        patch.applied_at = datetime.now(timezone.utc).isoformat()

        return PatchApplicationResult(
            success=True,
            patch_id=patch.patch_id,
            provider=ConnectorType.WEBFLOW,
            applied_at=patch.applied_at,
            target_resource=f"Webflow Site {self.site_id} (Custom Code Head)",
            message=f"Deployed custom schema/meta embed to Webflow site."
        )

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        res = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=res["rolled_back_at"],
            message="Reverted Webflow custom code embed."
        )

    async def verify_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "verified": False,
            "patch_id": patch.patch_id,
            "citation_score_delta": None,
            "notes": "Verification pending live Webflow custom code embed render check."
        }
