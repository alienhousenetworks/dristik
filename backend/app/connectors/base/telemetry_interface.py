"""
Dristik AI Standardized External Telemetry Interface & Models
Defines the typed contract for all external data connectors (GSC, GA4, CrUX, Backlinks)
with strict fail-closed state management and typed EvidenceRef generation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.evidence.models import EvidenceRef


class ExternalTelemetryResult(BaseModel):
    connector_id: str
    connector_name: str
    domain: str
    status: Literal["CONNECTED", "NOT_CONNECTED", "UNAVAILABLE", "ERROR"]
    is_connected: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)
    evidence_ref: Optional[EvidenceRef] = None
    unavailability_reason: Optional[str] = None
    lab_fallback_only: bool = False
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    provenance_label: str = "LIVE_EXTERNAL_QUERY"


class ExternalTelemetryConnector(ABC):
    """
    Uniform contract implemented by all first-party and third-party data providers.
    Enforces fail-closed error handling and zero synthetic fixture injection.
    """

    @abstractmethod
    async def fetch_telemetry(self, domain: str, **kwargs: Any) -> ExternalTelemetryResult:
        """
        Queries the external API or returns an explicit fail-closed UNCONNECTED result.
        """
        pass
