"""
Dristik AI WordPress Remediation Adapter
Translates Universal RemediationPatch into WordPress API operations.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from app.domain.models import RemediationPatch
from app.domain.enums import ConnectorType, PatchApprovalStatus, PatchOperation
from app.connectors.base.models import PatchApplicationResult, RollbackResult
from app.connectors.base.permissions import ConnectorSecurityGuard
from app.connectors.wordpress.client import WordPressClient
from app.remediation.rollback import rollback_engine

class WordPressRemediation:
    def __init__(self, client: WordPressClient):
        self.client = client

    async def preview(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "platform": "WordPress",
            "operation": patch.operation.value,
            "target": patch.target_url,
            "action_type": "wp_head_injection" if patch.operation in [PatchOperation.UPDATE_JSONLD, PatchOperation.INSERT_HEAD] else "wp_robots_filter",
            "payload_preview": patch.after_snippet,
            "reversible": True
        }

    async def apply(self, patch: RemediationPatch) -> PatchApplicationResult:
        # 1. Security boundary check
        ConnectorSecurityGuard.validate_patch_permissions(patch, "wordpress")

        # 2. Capture rollback snapshot
        rollback_engine.capture_pre_patch_snapshot(patch, {
            "platform": "wordpress",
            "previous_snippet": patch.before_snippet,
            "target": patch.target_url
        })

        applied_at = datetime.now(timezone.utc).isoformat()
        return PatchApplicationResult(
            success=False,
            patch_id=patch.patch_id,
            provider=ConnectorType.WORDPRESS,
            applied_at=applied_at,
            target_resource=self.client.base_url or "",
            diff_summary={"operation": patch.operation.value, "title": patch.title},
            message="WordPress was not updated. No REST or plugin call was made."
        )

    async def rollback(self, patch: RemediationPatch) -> RollbackResult:
        result = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=result["rolled_back_at"],
            message=f"Reverted WordPress changes for patch {patch.patch_id}."
        )
