"""
Dristik AI GitHub Connector
Subclass of BaseConnector for repository management, Next.js/React framework detection, and Pull Requests.
"""
from typing import Dict, Any
from app.connectors.base.interface import BaseConnector
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult
)
from app.domain.models import RemediationPatch
from app.connectors.github.client import GitHubClient
from app.connectors.github.discovery import GitHubDiscovery
from app.connectors.github.remediation import GitHubRemediation
from app.connectors.github.verify import GitHubVerifier

class GitHubConnector(BaseConnector):
    def __init__(self, credentials: ConnectorCredentials):
        super().__init__(credentials)
        self.client = GitHubClient(credentials)
        self.discovery = GitHubDiscovery(self.client)
        self.remediation = GitHubRemediation(self.client)
        self.verifier = GitHubVerifier(self.client.repo)

    async def test_connection(self) -> ConnectorHealth:
        return await self.client.test_health()

    async def discover_site_structure(self) -> Dict[str, Any]:
        return await self.discovery.discover()

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return await self.remediation.preview(patch)

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        return await self.remediation.apply(patch)

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        return await self.remediation.rollback(patch)

    async def verify_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return await self.verifier.verify_patch(patch)

__all__ = ["GitHubConnector"]
