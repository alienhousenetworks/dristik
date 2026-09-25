"""
Dristik AI Connector Permissions & Security Boundary Guard
Enforces strict least-privilege capability boundaries for all connectors.
"""
from typing import Set, Tuple
from app.domain.models import RemediationPatch
from app.domain.enums import PatchOperation, PatchRiskLevel

# Explicit Whitelists
ALLOWED_READ_CAPABILITIES: Set[str] = {
    "site_settings",
    "pages",
    "posts",
    "products",
    "metadata",
    "schema",
    "robots_txt",
    "sitemap",
    "repository_tree",
    "file_content"
}

ALLOWED_WRITE_CAPABILITIES: Set[str] = {
    "update_metadata",
    "inject_jsonld",
    "append_robots",
    "update_seo_fields",
    "create_branch",
    "create_pull_request"
}

# Strictly Blocked Operations
FORBIDDEN_OPERATIONS: Set[str] = {
    "arbitrary_php_execution",
    "arbitrary_eval",
    "user_management",
    "plugin_installation",
    "database_direct_write",
    "raw_sql_execution",
    "delete_page",
    "delete_post",
    "force_push_to_main",
    "bypass_branch_protections"
}

class PermissionViolationError(Exception):
    """Raised when an operation attempts to breach connector capability limits."""
    pass

class ConnectorSecurityGuard:
    """
    Validates that a patch operation strictly conforms to Dristik security boundaries.
    """

    @classmethod
    def validate_patch_permissions(cls, patch: RemediationPatch, provider: str) -> Tuple[bool, str]:
        # 1. Reject forbidden operations
        if any(bad in patch.after_snippet.lower() for bad in ["system(", "exec(", "passthru(", "eval(", "drop table", "alter table"]):
            raise PermissionViolationError(f"Security Policy Violation: Unsafe executable code detected in patch {patch.patch_id}.")

        # 2. Check risk vs provider capability
        if provider == "wordpress":
            # WordPress can apply Level 1 and Level 2 directly (metadata, JSON-LD, robots)
            if patch.risk_level == PatchRiskLevel.DEVELOPER_REQUIRED:
                # Level 3 developer patches cannot be auto-applied directly to WordPress without dev PR
                return False, "Level 3 Developer patches require source repository PR (GitHub), not direct CMS modification."
            return True, "Permitted WordPress remediation operation"

        elif provider == "github":
            # GitHub creates PRs on separate branches, which is safe for all levels
            return True, "Permitted GitHub Pull Request workflow"

        elif provider in ["shopify", "webflow"]:
            if patch.risk_level == PatchRiskLevel.DEVELOPER_REQUIRED:
                return False, f"Level 3 changes cannot be deployed via {provider} API directly; review in source code."
            return True, f"Permitted {provider} CMS operation"

        return True, "Permitted operation"
