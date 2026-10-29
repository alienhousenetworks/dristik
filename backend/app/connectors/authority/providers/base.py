"""Provider contract for external authority data.

Capabilities are explicit. A provider does not invent metrics outside them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.connectors.authority.models import (
    AuthMode,
    CollectionResult,
    CollectionTier,
    ProviderCapabilities,
)


@dataclass
class CollectContext:
    project_id: str
    provider_id: str
    domain: str
    period_days: int
    property_id: Optional[str]
    access_token: Optional[str]
    api_key: Optional[str]
    login: Optional[str]
    password: Optional[str]
    brand_terms: List[str]
    transport: Any
    now: datetime
    mode: str = "default"
    inspect_urls: List[str] = field(default_factory=list)
    period_start: str = ""
    period_end: str = ""
    previous_start: str = ""
    previous_end: str = ""
    external_account_id: Optional[str] = None
    applicability: str = "UNKNOWN"


class ExternalDataProvider(ABC):
    provider_id: str
    display_name: str
    auth_mode: AuthMode
    capabilities: ProviderCapabilities
    collection_tier: CollectionTier
    scopes: List[str]

    def enabled(self) -> bool:
        return True

    def current_auth_mode(self) -> str:
        return self.auth_mode

    def application_credentials(self) -> Optional[Dict[str, Any]]:
        """Server-to-server credentials from the environment, if this provider uses them."""
        return None

    def oauth_application_ready(self) -> bool:
        return False

    @abstractmethod
    def authenticate(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        """Validate or exchange credentials. Must not log the secret."""

    def disconnect(self, secret: Dict[str, Any], transport: Any) -> None:
        """Best-effort revocation. Failures are ignored by the caller."""
        return None

    def refresh_credentials(self, secret: Dict[str, Any], transport: Any) -> Dict[str, Any]:
        return secret

    def get_account_properties(self, ctx: CollectContext) -> List[Any]:
        return []

    def get_site_properties(self, ctx: CollectContext) -> List[Any]:
        return []

    @abstractmethod
    def collect(self, ctx: CollectContext) -> CollectionResult:
        """Fetch one period. Must not fabricate metrics."""

    def health_check(self, ctx: Optional[CollectContext], connection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        connected = bool(connection and connection.get("status") == "CONNECTED")
        return {
            "provider": self.provider_id,
            "display_name": self.display_name,
            "connection_status": connection.get("status") if connection else "NOT_CONNECTED",
            "authenticated": connected,
            "capabilities": self.capabilities.model_dump(),
            "message": "Healthy" if connected else "Not connected",
        }


def not_connected(provider: str, note: str) -> CollectionResult:
    return CollectionResult(
        provider=provider,
        connection_status="NOT_CONNECTED",
        data_state="NOT_CONNECTED",
        note=note,
    )


def unavailable(provider: str, note: str, partial: Optional[List[str]] = None) -> CollectionResult:
    return CollectionResult(
        provider=provider,
        connection_status="CONNECTED",
        data_state="UNAVAILABLE",
        error=note,
        partial_errors=partial or [],
        note=note,
    )
