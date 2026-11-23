"""
Dristik AI GitHub Remediation Adapter
Creates remediation branches and generates Pull Requests with before/after diffs.
"""
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from app.domain.models import RemediationPatch
from app.domain.enums import ConnectorType, PatchApprovalStatus
from app.connectors.base.models import PatchApplicationResult, RollbackResult
from app.connectors.base.permissions import ConnectorSecurityGuard
from app.connectors.github.client import GitHubClient
from app.remediation.diff_engine import diff_engine
from app.remediation.rollback import rollback_engine

class GitHubRemediation:
    execution_mode = "LIVE"

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
            "commit_message": f"fix(geo): {patch.title} [{patch.finding_id}]",
        }

    async def apply(
        self,
        patch: RemediationPatch,
        *,
        dry_run: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> PatchApplicationResult:
        # 1. Security boundary check
        ConnectorSecurityGuard.validate_patch_permissions(patch, "github")

        # 2. Capture rollback snapshot
        rollback_engine.capture_pre_patch_snapshot(patch, {
            "platform": "github",
            "repository": self.client.repo,
            "branch": self.client.default_branch,
        })

        applied_at = datetime.now(timezone.utc).isoformat()
        repo = (self.client.repo or "").strip()
        token = (self.client.token or "").strip()
        target_file = (patch.target_file or f"docs/geo/{patch.patch_id.lower()}.md").lstrip("/")

        if dry_run or not token or "/" not in repo:
            return PatchApplicationResult(
                success=False,
                patch_id=patch.patch_id,
                provider=ConnectorType.GITHUB,
                applied_at=applied_at,
                target_resource=repo,
                execution_mode="PREVIEW_ONLY",
                diff_summary={"repo": repo, "target_file": target_file},
                pr_url=None,
                pr_number=None,
                message="No pull request was opened (dry_run enabled or missing GitHub token/repo).",
            )

        headers = self.client._headers()
        base_branch = self.client.default_branch or "main"
        branch_name = f"dristik/fix-{patch.patch_id.lower()}"
        api = f"https://api.github.com/repos/{repo}"

        async def _execute(client: httpx.AsyncClient) -> PatchApplicationResult:
            # Step 1: Get base branch HEAD SHA
            ref_r = await client.get(f"{api}/git/ref/heads/{base_branch}", headers=headers, timeout=20.0)
            if ref_r.status_code != 200:
                return PatchApplicationResult(
                    success=False, patch_id=patch.patch_id, provider=ConnectorType.GITHUB,
                    applied_at=applied_at, target_resource=repo, execution_mode="LIVE",
                    message=f"Failed to read base branch '{base_branch}': HTTP {ref_r.status_code}",
                )
            base_sha = ref_r.json()["object"]["sha"]

            # Step 2: Create remediation branch (422 = branch already exists -> idempotent)
            br_r = await client.post(
                f"{api}/git/refs",
                headers=headers,
                json={"ref": f"refs/heads/{branch_name}", "sha": base_sha},
                timeout=20.0,
            )
            if br_r.status_code not in (200, 201, 422):
                return PatchApplicationResult(
                    success=False, patch_id=patch.patch_id, provider=ConnectorType.GITHUB,
                    applied_at=applied_at, target_resource=repo, execution_mode="LIVE",
                    message=f"Failed to create branch '{branch_name}': HTTP {br_r.status_code}",
                )

            # Step 3: Commit file via Contents API
            content_url = f"{api}/contents/{target_file}"
            put_body: Dict[str, Any] = {
                "message": f"fix(geo): {patch.title} [{patch.finding_id}]",
                "branch": branch_name,
                "content": base64.b64encode((patch.after_snippet or "").encode("utf-8")).decode("ascii"),
            }
            existing_r = await client.get(content_url, headers=headers, params={"ref": branch_name}, timeout=20.0)
            if existing_r.status_code == 200 and existing_r.json().get("sha"):
                put_body["sha"] = existing_r.json()["sha"]

            put_r = await client.put(content_url, headers=headers, json=put_body, timeout=20.0)
            if put_r.status_code not in (200, 201):
                return PatchApplicationResult(
                    success=False, patch_id=patch.patch_id, provider=ConnectorType.GITHUB,
                    applied_at=applied_at, target_resource=repo, execution_mode="LIVE",
                    message=f"Failed to commit '{target_file}': HTTP {put_r.status_code}",
                )

            # Step 4: Open Pull Request
            pr_r = await client.post(
                f"{api}/pulls",
                headers=headers,
                json={
                    "title": f"[Dristik GEO] {patch.title}",
                    "head": branch_name,
                    "base": base_branch,
                    "body": f"Automated GEO/AEO remediation for finding `{patch.finding_id}` (`{patch.patch_id}`).",
                },
                timeout=20.0,
            )
            if pr_r.status_code in (200, 201):
                pr_data = pr_r.json()
                return PatchApplicationResult(
                    success=True,
                    patch_id=patch.patch_id,
                    provider=ConnectorType.GITHUB,
                    applied_at=applied_at,
                    target_resource=f"{repo}:{target_file}",
                    execution_mode="LIVE",
                    diff_summary={"repo": repo, "branch": branch_name, "target_file": target_file},
                    pr_url=pr_data.get("html_url"),
                    pr_number=pr_data.get("number"),
                    message=f"Opened GitHub PR #{pr_data.get('number')} on {repo}.",
                )
            return PatchApplicationResult(
                success=False, patch_id=patch.patch_id, provider=ConnectorType.GITHUB,
                applied_at=applied_at, target_resource=repo, execution_mode="LIVE",
                message=f"Committed file on '{branch_name}' but PR creation returned HTTP {pr_r.status_code}.",
            )

        try:
            if http_client is not None:
                return await _execute(http_client)
            async with httpx.AsyncClient(timeout=20.0) as client:
                return await _execute(client)
        except Exception as exc:
            return PatchApplicationResult(
                success=False, patch_id=patch.patch_id, provider=ConnectorType.GITHUB,
                applied_at=applied_at, target_resource=repo, execution_mode="LIVE",
                message=f"GitHub publish failed: {exc}",
            )

    async def rollback(self, patch: RemediationPatch) -> RollbackResult:
        result = rollback_engine.rollback(patch)
        return RollbackResult(
            success=True,
            patch_id=patch.patch_id,
            rolled_back_at=result["rolled_back_at"],
            message=f"Closed and rolled back GitHub remediation for PR #{patch.pr_number}."
        )
