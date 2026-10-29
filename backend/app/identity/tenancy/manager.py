"""
Dristik AI Tenant Manager & Partitioning Engine
Enforces tenant isolation across all storage operations and mission execution.
"""
from typing import Dict, Optional, List
import time
from app.identity.tenancy.models import Organization, Workspace, Project, MissionSnapshot
from app.domain.enums import DataResidency

class TenantManager:
    """In-memory enterprise tenant registry and query scoping enforcement engine."""

    def __init__(self):
        self._orgs: Dict[str, Organization] = {}
        self._workspaces: Dict[str, Workspace] = {}
        self._projects: Dict[str, Project] = {}
        self._snapshots: Dict[str, MissionSnapshot] = {}

        # Default system organization for single-tenant / local development
        default_org = Organization(
            org_id="org_default",
            name="Default Organization",
            slug="default-org",
            plan="enterprise",
            data_residency=DataResidency.GLOBAL,
            allowed_domains=["*"],
            budget_limit_usd=1000.0
        )
        self._orgs[default_org.org_id] = default_org

        default_ws = Workspace(
            workspace_id="ws_default",
            org_id="org_default",
            name="Default Workspace",
            slug="default-ws"
        )
        self._workspaces[default_ws.workspace_id] = default_ws

    def register_organization(
        self,
        name: str,
        slug: str,
        plan: str = "enterprise",
        allowed_domains: Optional[List[str]] = None,
        data_residency: DataResidency = DataResidency.GLOBAL,
        budget_limit_usd: float = 500.0
    ) -> Organization:
        org = Organization(
            name=name,
            slug=slug,
            plan=plan,
            allowed_domains=allowed_domains or ["*"],
            data_residency=data_residency,
            budget_limit_usd=budget_limit_usd
        )
        self._orgs[org.org_id] = org
        return org

    def get_organization(self, org_id: str) -> Optional[Organization]:
        org = self._orgs.get(org_id)
        if org and org.deleted_at is None and org.is_active:
            return org
        return None

    def validate_tenant_access(self, org_id: str, target_domain: str) -> bool:
        """Validates that the organization exists, is active, within budget, and allows target domain."""
        org = self.get_organization(org_id)
        if not org:
            return False

        if org.budget_used_usd >= org.budget_limit_usd:
            return False

        if "*" in org.allowed_domains:
            return True

        normalized_domain = target_domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
        return any(
            normalized_domain == allowed or normalized_domain.endswith("." + allowed)
            for allowed in org.allowed_domains
        )

    def record_cost(self, org_id: str, cost_usd: float):
        org = self._orgs.get(org_id)
        if org:
            org.budget_used_usd += cost_usd

    def soft_delete_organization(self, org_id: str) -> bool:
        org = self._orgs.get(org_id)
        if not org:
            return False
        if org.is_legal_hold:
            raise PermissionError("Cannot delete organization currently under legal hold.")
        org.deleted_at = time.time()
        org.is_active = False
        return True

    def purge_organization_data(self, org_id: str) -> bool:
        """Tenant-initiated GDPR/CCPA hard purge."""
        org = self._orgs.get(org_id)
        if not org:
            return False
        if org.is_legal_hold:
            raise PermissionError("Cannot purge organization currently under legal hold.")

        self._orgs.pop(org_id, None)
        # Purge workspaces, projects, snapshots
        self._workspaces = {k: v for k, v in self._workspaces.items() if v.org_id != org_id}
        self._projects = {k: v for k, v in self._projects.items() if v.org_id != org_id}
        self._snapshots = {k: v for k, v in self._snapshots.items() if v.org_id != org_id}
        return True

tenant_manager = TenantManager()
