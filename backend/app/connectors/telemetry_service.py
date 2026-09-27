"""
Dristik AI External Telemetry Ingestion Service
Coordinates concurrent polling across GSC, GA4, CrUX, and External SEO connectors.
Ingests live external signals into the Evidence Graph with typed EvidenceRefs,
and surfaces clean fail-closed notices when integrations are unconnected.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evidence.models import Evidence, EvidenceRef
from app.connectors.base.telemetry_interface import ExternalTelemetryResult
from app.connectors.base.models import ConnectorCredentials
from app.domain.enums import ConnectorType
from app.connectors.google.connector import GoogleSearchConsoleConnector
from app.connectors.google.ga4_connector import GoogleAnalytics4Connector
from app.connectors.crux.connector import CruxConnector
from app.connectors.external_seo.connector import ExternalSeoConnector

logger = logging.getLogger("dristik.connectors.telemetry_service")


class ExternalTelemetryPackage(BaseModel):
    domain: str
    queried_at: datetime = Field(default_factory=datetime.utcnow)
    all_connected: bool = False
    connected_count: int = 0
    total_connectors: int = 4
    results: Dict[str, ExternalTelemetryResult] = Field(default_factory=dict)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)

    def to_coverage_connector_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Maps connector telemetry results to the structure expected by EvidenceCoverageCalculator.
        """
        cov_dict = {}
        mapping = {
            "gsc": "google_search_console",
            "ga4": "google_analytics_4",
            "crux": "crux_origin_field_data",
            "external_seo": "third_party_backlinks",
        }
        for c_id, cov_key in mapping.items():
            res = self.results.get(c_id)
            if res and res.is_connected:
                cov_dict[cov_key] = {
                    "name": res.connector_name,
                    "status": "MEASURED",
                    "metrics": res.metrics,
                    "note": "Live external query verified.",
                }
            elif res and res.status == "UNAVAILABLE":
                cov_dict[cov_key] = {
                    "name": res.connector_name,
                    "status": "UNAVAILABLE",
                    "unavailability_reason": res.unavailability_reason,
                    "note": res.unavailability_reason or "Resource unavailable for this domain.",
                }
            else:
                cov_dict[cov_key] = {
                    "name": res.connector_name if res else cov_key,
                    "status": "NOT_CONNECTED",
                    "unavailability_reason": res.unavailability_reason if res else "Connector unconfigured.",
                    "note": res.unavailability_reason if res else "Connector unconfigured.",
                }
        return cov_dict


class ExternalTelemetryService:
    """
    Orchestrates parallel external telemetry acquisition.
    """

    def __init__(
        self,
        gsc: Optional[GoogleSearchConsoleConnector] = None,
        ga4: Optional[GoogleAnalytics4Connector] = None,
        crux: Optional[CruxConnector] = None,
        external_seo: Optional[ExternalSeoConnector] = None,
    ):
        self.gsc = gsc or GoogleSearchConsoleConnector(ConnectorCredentials(provider=ConnectorType.GOOGLE_SEARCH_CONSOLE))
        self.ga4 = ga4 or GoogleAnalytics4Connector(ConnectorCredentials(provider=ConnectorType.GOOGLE_ANALYTICS_4))
        self.crux = crux or CruxConnector(ConnectorCredentials(provider=ConnectorType.CRUX))
        self.external_seo = external_seo or ExternalSeoConnector(ConnectorCredentials(provider=ConnectorType.DATAFORSEO))

    async def fetch_all_telemetry(
        self,
        domain: str,
        evidence_store: Optional[Any] = None,
    ) -> ExternalTelemetryPackage:
        """
        Concurrently queries all 4 external data providers.
        """
        tasks = [
            self._safe_fetch("gsc", self.gsc, domain),
            self._safe_fetch("ga4", self.ga4, domain),
            self._safe_fetch("crux", self.crux, domain),
            self._safe_fetch("external_seo", self.external_seo, domain),
        ]

        raw_results = await asyncio.gather(*tasks)
        results: Dict[str, ExternalTelemetryResult] = {r.connector_id: r for r in raw_results}

        evidence_refs: List[EvidenceRef] = []
        connected_count = 0

        for r in results.values():
            if r.is_connected:
                connected_count += 1
                if r.evidence_ref:
                    evidence_refs.append(r.evidence_ref)
                    if evidence_store and hasattr(evidence_store, "add_evidence"):
                        evidence_store.add_evidence(
                            source_type="external",
                            analyzer=f"connector_{r.connector_id}",
                            url=f"https://{domain}",
                            text=r.evidence_ref.snippet or f"{r.connector_name} metrics",
                            value=r.metrics,
                            metadata=r.evidence_ref.metadata,
                        )

        all_connected = (connected_count == len(results))

        return ExternalTelemetryPackage(
            domain=domain,
            all_connected=all_connected,
            connected_count=connected_count,
            total_connectors=len(results),
            results=results,
            evidence_refs=evidence_refs,
        )

    async def _safe_fetch(
        self,
        cid: str,
        connector: Any,
        domain: str,
    ) -> ExternalTelemetryResult:
        try:
            return await connector.fetch_telemetry(domain)
        except Exception as e:
            logger.error("[ExternalTelemetryService] Error in connector '%s': %s", cid, e)
            return ExternalTelemetryResult(
                connector_id=cid,
                connector_name=cid.upper(),
                domain=domain,
                status="ERROR",
                is_connected=False,
                unavailability_reason=f"Connector error: {str(e)}",
                provenance_label="UNCONNECTED_FALLBACK",
            )
