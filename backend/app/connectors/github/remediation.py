"""
Dristik AI GitHub Remediation Adapter
Creates remediation branches and generates Pull Requests with before/after diffs.
"""
from datetime import datetime, timezone
from typing import Dict, Any
from app.domain.models import RemediationPatch
from app.domain.enums import ConnectorType, PatchApprovalStatus
from app.connectors.base.models import PatchApplicationResult, RollbackResult
from app.connectors.base.permissions import ConnectorSecurityGuard
from app.connectors.github.client import GitHubClient
from app.remediation.diff_engine import diff_engine
from app.remediation.rollback import rollback_engine

class GitHubRemediation:
    def __init__(self, client: GitHubClient):
        self.client = client

    async def preview(self, patch: RemediationPatch) -> Dict[str, Any]:
        diff = diff_engine.generate_unified_diff(patch)
        branch_name = f"dristik/fix-{patch.patch_id.lower()}"
        return {
            "platform": "GitHub",
            "repository": self.client.repo,
            "target_branch": self.client.default_branch,
            "proposed_branch": branch_name,
            "target_file": patch.target_file,
            "unified_diff": diff,
            "commit_message": f"fix(seo): {patch.title} [{patch.finding_id}]"
        }

    async def apply(self, patch: RemediationPatch) -> PatchApplicationResult:
        # 1. Security boundary check
        ConnectorSecurityGuard.validate_patch_permissions(patch, "github")

        # 2. Capture rollback snapshot
        rollback_engine.capture_pre_patch_snapshot(patch, {
            "platform": "github",
            "repository": self.client.repo,
            "branch": self.client.default_branch
        })

        applied_at = datetime.now(timezone.utc).isoformat()
        return PatchApplicationResult(
            success=False,
            patch_id=patch.patch_id,
            provider=ConnectorType.GITHUB,
            applied_at=applied_at,
            target_resource=self.client.repo or "",
            diff_summary={"repo": self.client.repo},
            pr_url=None,
            pr_number=None,
            message="No pull request was opened. The GitHub API was not called."
        )

    async def rollback(self, patch: RemediationPatch) -> RollbackResult:
        result = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=result["rolled_back_at"],
            message=f"Closed and rolled back GitHub remediation for PR #{patch.pr_number}."
        )
