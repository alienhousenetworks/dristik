"""
Dristik AI Connector Abstract Base Class
Defines the uniform lifecycle interface for all platform integrations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.domain.models import RemediationPatch
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult
)

class BaseConnector(ABC):
    """
    Uniform contract that all website/platform connectors must implement.
    """

    def __init__(self, credentials: ConnectorCredentials):
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> ConnectorHealth:
        """Ping the external platform and verify authentication and health."""
        pass

    @abstractmethod
    async def discover_site_structure(self) -> Dict[str, Any]:
        """Fetch metadata, pages, posts, or repository structure."""
        pass

    @abstractmethod
    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        """Generate platform-specific translation and preview of the patch."""
        pass

    @abstractmethod
    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        """Safely deploy the patch through the platform's API or create a PR."""
        pass

    @abstractmethod
    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        """Revert the patch using the platform's API."""
        pass
