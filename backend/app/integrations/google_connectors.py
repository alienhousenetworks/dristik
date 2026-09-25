"""
Google Search Console (GSC) & Google Analytics 4 (GA4) First-Party Connectors
Connects strictly to live Google APIs or returns clean unconfigured states.
Zero synthetic or fabricated fixture metrics permitted in production.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import MetricProvenanceState

logger = logging.getLogger(__name__)


class GscQueryItem(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    provenance: MetricProvenanceState = MetricProvenanceState.MEASURED


class GscPerformanceSummary(BaseModel):
    connected: bool
    domain: str
    provenance: MetricProvenanceState = MetricProvenanceState.NOT_CONFIGURED
    total_clicks: int = 0
    total_impressions: int = 0
    average_ctr: float = 0.0
    average_position: float = 0.0
    queries: List[GscQueryItem] = Field(default_factory=list)
    crawl_coverage_errors: List[str] = Field(default_factory=list)
    source: str = "google_search_console_v1"
    status_notice: Optional[str] = None


class Ga4PerformanceSummary(BaseModel):
    connected: bool
    property_id: Optional[str] = None
    domain: str
    provenance: MetricProvenanceState = MetricProvenanceState.NOT_CONFIGURED
    sessions_30d: int = 0
    engagement_rate: float = 0.0
    bounce_rate: float = 0.0
    avg_session_duration_sec: float = 0.0
    conversions_count: int = 0
    conversion_rate: float = 0.0
    top_landing_pages: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "google_analytics_4_data_api"
    status_notice: Optional[str] = None


class GoogleSearchConsoleConnector:
    """Queries Google Search Console Search Analytics API. Fail-closed without fake fixtures."""

    def __init__(self, credentials_json: Optional[str] = None):
        from app.core.config import settings
        if credentials_json is None:
            credentials_json = settings.GOOGLE_APPLICATION_CREDENTIALS or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.credentials_json = credentials_json or None
        self._connected = bool(self.credentials_json and self.verify_credentials(self.credentials_json))

    @property
    def is_connected(self) -> bool:
        return self._connected

    def verify_credentials(self, credentials_path: str) -> bool:
        """Validates that credentials file exists and contains valid JSON service account keys."""
        if not credentials_path or not os.path.exists(credentials_path):
            return False
        try:
            with open(credentials_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("type") == "service_account" and bool(data.get("private_key")) and bool(data.get("client_email"))
        except Exception as e:
            logger.warning(f"[GSC] Credential validation failed: {e}")
            return False

    def fetch_performance(self, domain: str, days: int = 90) -> GscPerformanceSummary:
        """Fetches search performance metrics. Returns NOT_CONFIGURED when unconnected."""
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        if not self._connected:
            return GscPerformanceSummary(
                connected=False,
                domain=clean_domain,
                provenance=MetricProvenanceState.NOT_CONFIGURED,
                total_clicks=0,
                total_impressions=0,
                average_ctr=0.0,
                average_position=0.0,
                queries=[],
                crawl_coverage_errors=[],
                source="google_search_console_v1",
                status_notice="Google Search Console is not configured. Connect authorized service account credentials to stream verified search clicks and impressions.",
            )

        try:
            from app.integrations.google_api import query_search_console
            payload = query_search_console(self.credentials_json or "", clean_domain, days=days)
        except Exception as exc:
            logger.warning("[GSC] Live query failed for %s: %s", clean_domain, exc)
            return GscPerformanceSummary(
                connected=False,
                domain=clean_domain,
                provenance=MetricProvenanceState.FAILED,
                source="google_search_console_v1",
                status_notice=f"Google Search Console query failed: {exc}",
            )
        rows = payload.get("rows") or []
        queries: List[GscQueryItem] = []
        clicks = impressions = 0
        weighted_position = 0.0
        for row in rows:
            keys = row.get("keys") or []
            if not keys:
                continue
            row_clicks = int(row.get("clicks") or 0)
            row_impressions = int(row.get("impressions") or 0)
            clicks += row_clicks
            impressions += row_impressions
            weighted_position += float(row.get("position") or 0) * row_impressions
            queries.append(GscQueryItem(
                query=str(keys[0]),
                clicks=row_clicks,
                impressions=row_impressions,
                ctr=float(row.get("ctr") or 0),
                position=float(row.get("position") or 0),
                provenance=MetricProvenanceState.MEASURED,
            ))
        return GscPerformanceSummary(
            connected=True,
            domain=clean_domain,
            provenance=MetricProvenanceState.MEASURED,
            total_clicks=clicks,
            total_impressions=impressions,
            average_ctr=(clicks / impressions) if impressions else 0.0,
            average_position=(weighted_position / impressions) if impressions else 0.0,
            queries=queries,
            crawl_coverage_errors=[],
            source="gsc_verified_oauth",
            status_notice="Measured from the Google Search Console Search Analytics API.",
        )


class GoogleAnalytics4Connector:
    """Queries GA4 Data API. Fail-closed without fake fixtures."""

    def __init__(self, property_id: Optional[str] = None, credentials_json: Optional[str] = None):
        from app.core.config import settings
        if property_id is None:
            property_id = settings.GA4_PROPERTY_ID or os.getenv("GA4_PROPERTY_ID")
        self.property_id = property_id or None
        self._credentials_json = credentials_json
        creds = self.credentials_path()
        self._connected = bool(self.property_id and self.property_id.strip() and creds and self.verify_credentials(creds))

    def credentials_path(self) -> Optional[str]:
        from app.core.config import settings
        if self._credentials_json:
            return self._credentials_json
        return settings.GOOGLE_APPLICATION_CREDENTIALS or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    def verify_credentials(self, credentials_path: str) -> bool:
        if not credentials_path or not os.path.exists(credentials_path):
            return False
        try:
            with open(credentials_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data.get("type") == "service_account" and bool(data.get("private_key")) and bool(data.get("client_email"))
        except Exception as exc:
            logger.warning("[GA4] Credential validation failed: %s", exc)
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def verify_property_id(self, prop_id: str) -> bool:
        """Validates that GA4 property ID is non-empty and formatted appropriately."""
        clean = prop_id.strip() if prop_id else ""
        return bool(clean and (clean.isdigit() or clean.startswith("properties/")))

    def fetch_performance(self, domain: str) -> Ga4PerformanceSummary:
        """Fetches visitor engagement and conversion metrics. Returns NOT_CONFIGURED when unconnected."""
        clean_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

        if not self._connected:
            return Ga4PerformanceSummary(
                connected=False,
                property_id=None,
                domain=clean_domain,
                provenance=MetricProvenanceState.NOT_CONFIGURED,
                sessions_30d=0,
                engagement_rate=0.0,
                bounce_rate=0.0,
                avg_session_duration_sec=0.0,
                conversions_count=0,
                conversion_rate=0.0,
                top_landing_pages=[],
                source="google_analytics_4_data_api",
                status_notice="Google Analytics 4 is not connected. Enter a verified GA4 Property ID to stream live session and conversion telemetry.",
            )

        credentials_path = self.credentials_path()
        if not credentials_path or not self.property_id:
            return Ga4PerformanceSummary(
                connected=False,
                property_id=self.property_id,
                domain=clean_domain,
                provenance=MetricProvenanceState.NOT_CONFIGURED,
                status_notice="Google Analytics 4 needs both a property ID and a service-account JSON.",
            )
        try:
            from app.integrations.google_api import query_ga4
            payload = query_ga4(credentials_path, self.property_id)
        except Exception as exc:
            logger.warning("[GA4] Live query failed for %s: %s", clean_domain, exc)
            return Ga4PerformanceSummary(
                connected=False,
                property_id=self.property_id,
                domain=clean_domain,
                provenance=MetricProvenanceState.FAILED,
                status_notice=f"GA4 Data API query failed: {exc}",
            )
        metric_headers = [h.get("name") for h in payload.get("metricHeaders") or []]
        rows = payload.get("rows") or []
        values = (rows[0].get("metricValues") if rows else []) or []
        parsed: Dict[str, float] = {}
        for name, cell in zip(metric_headers, values):
            raw = cell.get("value")
            try:
                parsed[name] = float(raw)
            except (TypeError, ValueError):
                continue
        if "sessions" not in parsed:
            return Ga4PerformanceSummary(
                connected=False,
                property_id=self.property_id,
                domain=clean_domain,
                provenance=MetricProvenanceState.FAILED,
                status_notice="GA4 Data API returned no sessions metric.",
            )
        sessions = int(parsed["sessions"])
        conversions = int(parsed["conversions"]) if "conversions" in parsed else 0
        return Ga4PerformanceSummary(
            connected=True,
            property_id=self.property_id,
            domain=clean_domain,
            provenance=MetricProvenanceState.MEASURED,
            sessions_30d=sessions,
            engagement_rate=parsed.get("engagementRate", 0.0),
            bounce_rate=parsed.get("bounceRate", 0.0),
            avg_session_duration_sec=parsed.get("averageSessionDuration", 0.0),
            conversions_count=conversions,
            conversion_rate=(conversions / sessions) if sessions else 0.0,
            top_landing_pages=[],
            source="ga4_verified_oauth",
            status_notice="Measured from the GA4 Data API for the last 30 days.",
        )


# Global singletons
gsc_connector = GoogleSearchConsoleConnector()
ga4_connector = GoogleAnalytics4Connector()
