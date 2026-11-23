"""
Dristik AI WordPress Remediation Adapter
Translates Universal RemediationPatch into WordPress API operations.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from app.core.security.ssrf import is_safe_url
from app.domain.models import RemediationPatch
from app.domain.enums import ConnectorType, PatchApprovalStatus, PatchOperation
from app.connectors.base.models import PatchApplicationResult, RollbackResult
from app.connectors.base.permissions import ConnectorSecurityGuard
from app.connectors.wordpress.client import WordPressClient
from app.remediation.rollback import rollback_engine

class WordPressRemediation:
    execution_mode = "LIVE"

    def __init__(self, client: WordPressClient):
        self.client = client

    async def preview(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {
            "platform": "WordPress",
            "operation": patch.operation.value,
            "target": patch.target_url,
            "action_type": "wp_draft_post" if patch.operation in (PatchOperation.INSERT_BODY, PatchOperation.UPDATE_FILE) else "wp_head_injection",
            "payload_preview": patch.after_snippet,
            "reversible": True,
        }

    async def apply(
        self,
        patch: RemediationPatch,
        *,
        dry_run: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> PatchApplicationResult:
        # 1. Security boundary check
        ConnectorSecurityGuard.validate_patch_permissions(patch, "wordpress")

        # 2. Capture rollback snapshot
        rollback_engine.capture_pre_patch_snapshot(patch, {
            "platform": "wordpress",
            "previous_snippet": patch.before_snippet,
            "target": patch.target_url,
        })

        applied_at = datetime.now(timezone.utc).isoformat()
        base_url = (self.client.base_url or "").rstrip("/")
        headers = self.client._get_auth_headers()
        has_auth = ("Authorization" in headers) or ("X-Dristik-Plugin-Key" in headers)

        if dry_run or not base_url or not has_auth:
            return PatchApplicationResult(
                success=False,
                patch_id=patch.patch_id,
                provider=ConnectorType.WORDPRESS,
                applied_at=applied_at,
                target_resource=base_url,
                execution_mode="PREVIEW_ONLY",
                diff_summary={"operation": patch.operation.value, "title": patch.title},
                message="WordPress was not updated (dry_run enabled or missing WordPress URL/credentials).",
            )

        endpoint = f"{base_url}/wp-json/wp/v2/posts"
        safe, reason = is_safe_url(endpoint)
        if not safe:
            return PatchApplicationResult(
                success=False,
                patch_id=patch.patch_id,
                provider=ConnectorType.WORDPRESS,
                applied_at=applied_at,
                target_resource=endpoint,
                execution_mode="LIVE",
                message=f"WordPress publish blocked by SSRF guard: {reason}",
            )

        payload = {
            "title": patch.title or f"GEO Update {patch.patch_id}",
            "content": patch.after_snippet or "",
            "status": "draft",
        }
        try:
            if http_client is not None:
                resp = await http_client.post(endpoint, headers=headers, json=payload, timeout=20.0)
            else:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                post_url = str(data.get("link") or "")
                post_id = data.get("id")
                return PatchApplicationResult(
                    success=True,
                    patch_id=patch.patch_id,
                    provider=ConnectorType.WORDPRESS,
                    applied_at=applied_at,
                    target_resource=post_url or endpoint,
                    execution_mode="LIVE",
                    diff_summary={
                        "operation": patch.operation.value,
                        "title": patch.title,
                        "wp_post_id": post_id,
                        "wp_status": data.get("status", "draft"),
                        "url": post_url,
                    },
                    message=f"Created WordPress draft post (id={post_id}). Review and publish in WP Admin.",
                )
            return PatchApplicationResult(
                success=False,
                patch_id=patch.patch_id,
                provider=ConnectorType.WORDPRESS,
                applied_at=applied_at,
                target_resource=endpoint,
                execution_mode="LIVE",
                message=f"WordPress REST API returned HTTP {resp.status_code}: {resp.text[:200]}",
            )
        except Exception as exc:
            return PatchApplicationResult(
                success=False,
                patch_id=patch.patch_id,
                provider=ConnectorType.WORDPRESS,
                applied_at=applied_at,
                target_resource=endpoint,
                execution_mode="LIVE",
                message=f"WordPress publish failed: {exc}",
            )

    async def rollback(self, patch: RemediationPatch) -> RollbackResult:
        result = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=result["rolled_back_at"],
            message=f"Reverted WordPress changes for patch {patch.patch_id}."
        )
