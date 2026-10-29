"""
Dristik AI WordPress Connector
Complete integration subclassing BaseConnector.
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
from app.connectors.wordpress.client import WordPressClient
from app.connectors.wordpress.discovery import WordPressDiscovery
from app.connectors.wordpress.remediation import WordPressRemediation
from app.connectors.wordpress.verify import WordPressVerifier

class WordPressConnector(BaseConnector):
    def __init__(self, credentials: ConnectorCredentials):
        super().__init__(credentials)
        self.client = WordPressClient(credentials)
        self.discovery = WordPressDiscovery(self.client)
        self.remediation = WordPressRemediation(self.client)
        self.verifier = WordPressVerifier(self.client.base_url)

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

__all__ = ["WordPressConnector"]
