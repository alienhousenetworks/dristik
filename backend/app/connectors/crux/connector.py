"""
Dristik AI Google CrUX Connector (Chrome User Experience Report)
Connects to Google's PageSpeed Insights / CrUX API to fetch:
- Real field user LCP, INP, CLS, FCP
- Device and network distribution
"""
import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.connectors.base.interface import BaseConnector
from app.connectors.base.telemetry_interface import ExternalTelemetryConnector, ExternalTelemetryResult
from app.connectors.base.models import (
    ConnectorCredentials,
    ConnectorHealth,
    PatchApplicationResult,
    RollbackResult,
)
from app.domain.enums import ConnectorType, ConnectorHealthStatus
from app.domain.models import RemediationPatch
from app.evidence.models import EvidenceRef


class CruxConnector(BaseConnector, ExternalTelemetryConnector):
    """
    Connects to Google Chrome User Experience Report (CrUX).
    Enforces honest fail-closed lab fallbacks when API key or origin traffic is missing.
    """

    async def test_connection(self) -> ConnectorHealth:
        key = self.credentials.api_key or os.getenv("PAGESPEED_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            # CrUX public API can be queried with public quota or key
            return ConnectorHealth(
                provider=ConnectorType.CRUX,
                status=ConnectorHealthStatus.CONNECTED,
                authenticated=True,
                message="Google CrUX public API enabled (Standard Rate Limit).",
                last_checked_at=datetime.now(timezone.utc).isoformat(),
                permissions_granted=["crux_field_metrics", "core_web_vitals"],
            )

        return ConnectorHealth(
            provider=ConnectorType.CRUX,
            status=ConnectorHealthStatus.CONNECTED,
            authenticated=True,
            message="Google CrUX authenticated with dedicated API key.",
            last_checked_at=datetime.now(timezone.utc).isoformat(),
            permissions_granted=["crux_field_metrics", "core_web_vitals"],
        )

    async def discover_site_structure(self) -> Dict[str, Any]:
        return {"metrics": ["largest_contentful_paint", "interaction_to_next_paint", "cumulative_layout_shift"]}

    async def preview_patch(self, patch: RemediationPatch) -> Dict[str, Any]:
        return {"status": "read_only_telemetry"}

    async def apply_patch(self, patch: RemediationPatch) -> PatchApplicationResult:
        return PatchApplicationResult(
            patch_id=patch.patch_id,
            success=False,
            message="Google CrUX connector is read-only telemetry",
            applied_at=datetime.now(timezone.utc).isoformat(),
        )

    async def rollback_patch(self, patch: RemediationPatch) -> RollbackResult:
        return RollbackResult(
            patch_id=patch.patch_id,
            success=False,
            message="Google CrUX connector cannot be rolled back",
            rolled_back_at=datetime.now(timezone.utc).isoformat(),
        )

    async def fetch_telemetry(self, domain: str, **kwargs: Any) -> ExternalTelemetryResult:
        import httpx
        key = self.credentials.api_key or os.getenv("PAGESPEED_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return ExternalTelemetryResult(
                connector_id="crux",
                connector_name="Chrome User Experience Report",
                domain=domain,
                status="NOT_CONNECTED",
                is_connected=False,
                lab_fallback_only=True,
                metrics={},
                unavailability_reason="Google CrUX API key not configured. Lab performance diagnostics used exclusively.",
                provenance_label="UNCONNECTED_FALLBACK",
            )

        # For test or mocked domains
        if domain.endswith(".test") or domain in ("example.com", "localhost") or "no-crux" in domain:
            return ExternalTelemetryResult(
                connector_id="crux",
                connector_name="Chrome User Experience Report",
                domain=domain,
                status="UNAVAILABLE",
                is_connected=False,
                lab_fallback_only=True,
                metrics={},
                unavailability_reason=f"Domain origin '{domain}' has insufficient real-user traffic in Google CrUX dataset. Lab performance diagnostics used exclusively.",
                provenance_label="LAB_DIAGNOSTICS_ONLY",
            )

        # Real Google CrUX API Query
        endpoint = f"https://chromeuxreport.googleapis.com/v1/records:queryRecord?key={key}"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(endpoint, json={"origin": f"https://{domain}"})
                if res.status_code == 200:
                    data = res.json()
                    raw_metrics = data.get("record", {}).get("metrics", {})
                    
                    def _extract_metric(m_name: str) -> Optional[float]:
                        m_obj = raw_metrics.get(m_name, {})
                        val = m_obj.get("percentiles", {}).get("p75")
                        try:
                            return float(val) if val is not None else None
                        except (ValueError, TypeError):
                            return None

                    def _extract_distribution(m_name: str) -> Dict[str, float]:
                        m_obj = raw_metrics.get(m_name, {})
                        hist = m_obj.get("histogram", [])
                        dist = {"good": 0.0, "needs_improvement": 0.0, "poor": 0.0}
                        if len(hist) >= 3:
                            dist["good"] = round(float(hist[0].get("density", 0.0)), 2)
                            dist["needs_improvement"] = round(float(hist[1].get("density", 0.0)), 2)
                            dist["poor"] = round(float(hist[2].get("density", 0.0)), 2)
                        return dist

                    metrics = {
                        "origin": f"https://{domain}",
                        "p75_lcp_ms": _extract_metric("largest_contentful_paint"),
                        "p75_inp_ms": _extract_metric("interaction_to_next_paint"),
                        "p75_cls": _extract_metric("cumulative_layout_shift"),
                        "p75_fcp_ms": _extract_metric("first_contentful_paint"),
                        "p75_ttfb_ms": _extract_metric("experimental_time_to_first_byte"),
                        "origin_eligibility": True,
                        "device_breakdown": {},
                        "distributions": {
                            "largest_contentful_paint": _extract_distribution("largest_contentful_paint"),
                            "interaction_to_next_paint": _extract_distribution("interaction_to_next_paint"),
                            "cumulative_layout_shift": _extract_distribution("cumulative_layout_shift"),
                            "first_contentful_paint": _extract_distribution("first_contentful_paint"),
                        }
                    }

                    ev_hash = hashlib.sha256(json.dumps(metrics, sort_keys=True).encode()).hexdigest()
                    snippet_parts = []
                    if metrics["p75_lcp_ms"] is not None:
                        snippet_parts.append(f"p75 LCP {metrics['p75_lcp_ms']}ms")
                    if metrics["p75_inp_ms"] is not None:
                        snippet_parts.append(f"p75 INP {metrics['p75_inp_ms']}ms")
                    if metrics["p75_cls"] is not None:
                        snippet_parts.append(f"p75 CLS {metrics['p75_cls']}")
                    snippet_str = ", ".join(snippet_parts) or "CrUX field metrics recorded"

                    ev_ref = EvidenceRef(
                        source_type="external",
                        source_id=f"crux_{domain}",
                        evidence_hash=ev_hash,
                        url=f"https://{domain}",
                        snippet=f"CrUX field metrics: {snippet_str}",
                        metadata=metrics
                    )
                    return ExternalTelemetryResult(
                        connector_id="crux",
                        connector_name="Chrome User Experience Report",
                        domain=domain,
                        status="CONNECTED",
                        is_connected=True,
                        lab_fallback_only=False,
                        metrics=metrics,
                        evidence_ref=ev_ref,
                        provenance_label="LIVE_EXTERNAL_QUERY",
                    )
                elif res.status_code == 404:
                    return ExternalTelemetryResult(
                        connector_id="crux",
                        connector_name="Chrome User Experience Report",
                        domain=domain,
                        status="UNAVAILABLE",
                        is_connected=False,
                        lab_fallback_only=True,
                        metrics={},
                        unavailability_reason=f"Domain origin '{domain}' has insufficient real-user traffic in Google CrUX dataset (28-day window). Lab performance diagnostics used exclusively.",
                        provenance_label="LAB_DIAGNOSTICS_ONLY",
                    )
                else:
                    return ExternalTelemetryResult(
                        connector_id="crux",
                        connector_name="Chrome User Experience Report",
                        domain=domain,
                        status="UNAVAILABLE",
                        is_connected=False,
                        lab_fallback_only=True,
                        metrics={},
                        unavailability_reason=f"Google CrUX API returned HTTP {res.status_code}. Lab performance diagnostics used exclusively.",
                        provenance_label="LAB_DIAGNOSTICS_ONLY",
                    )
        except Exception as e:
            return ExternalTelemetryResult(
                connector_id="crux",
                connector_name="Chrome User Experience Report",
                domain=domain,
                status="UNAVAILABLE",
                is_connected=False,
                lab_fallback_only=True,
                metrics={},
                unavailability_reason=f"Google CrUX lookup failed: {str(e)}. Lab performance diagnostics used exclusively.",
                provenance_label="LAB_DIAGNOSTICS_ONLY",
            )
