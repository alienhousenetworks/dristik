"""
DataForSEO & Majestic Pluggable Provider Interface
Provides live keyword search volumes, difficulty, CPC, and external backlink domain graphs.
Gracefully degrades with explicit unconfigured notices to eliminate fabricated metrics.
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums import MetricProvenanceState

logger = logging.getLogger(__name__)


class KeywordMetric(BaseModel):
    keyword: str
    search_volume: Optional[int] = None
    cpc_usd: Optional[float] = None
    competition: Optional[float] = None  # 0.0 to 1.0 when the API returns a ratio
    keyword_difficulty: Optional[int] = None  # omitted when the endpoint does not return it
    serp_features: List[str] = Field(default_factory=list)
    provenance: MetricProvenanceState = MetricProvenanceState.MEASURED


class KeywordFetchResult(BaseModel):
    domain: str
    connected: bool
    provenance: MetricProvenanceState
    keywords: List[KeywordMetric] = Field(default_factory=list)
    status_notice: str


class BacklinkProfileSummary(BaseModel):
    domain: str
    connected: bool
    provenance: MetricProvenanceState = MetricProvenanceState.NOT_CONNECTED
    referring_domains: Optional[int] = None
    total_backlinks: Optional[int] = None
    domain_rating: Optional[int] = None  # only when a provider actually returns it
    trust_flow: Optional[int] = None
    citation_flow: Optional[int] = None
    top_referring_tlds: List[Dict[str, Any]] = Field(default_factory=list)
    status_notice: str
    source: str = "dataforseo_majestic_link_graph"


class KeywordAndBacklinkProvider:
    """Manages live external search index and backlink crawler API requests."""

    def __init__(self, login: Optional[str] = None, password: Optional[str] = None):
        from app.core.config import settings
        if login is None:
            login = settings.DATAFORSEO_LOGIN or os.getenv("DATAFORSEO_LOGIN")
        if password is None:
            password = settings.DATAFORSEO_PASSWORD or os.getenv("DATAFORSEO_PASSWORD")
        self.login = login or None
        self.password = password or None
        self._connected = bool(self.login and self.password)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _seeds(self, clean_domain: str, seed_keywords: Optional[List[str]]) -> List[str]:
        brand = clean_domain.split(".")[0]
        return seed_keywords or [
            brand,
            f"{brand} platform",
            f"{brand} pricing",
            f"enterprise {brand}",
            f"{brand} alternatives",
        ]

    def _post(self, path: str, payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        import httpx
        response = httpx.post(
            f"https://api.dataforseo.com{path}",
            json=payload,
            auth=(self.login or "", self.password or ""),
            timeout=20.0,
        )
        if response.status_code != 200:
            raise RuntimeError(f"DataForSEO HTTP {response.status_code}: {response.text[:240]}")
        body = response.json()
        tasks = body.get("tasks") or []
        if not tasks:
            raise RuntimeError("DataForSEO returned no tasks.")
        task = tasks[0]
        if task.get("status_code") != 20000:
            raise RuntimeError(task.get("status_message") or f"DataForSEO task status {task.get('status_code')}")
        return task

    @staticmethod
    def _competition_ratio(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            number = float(value)
            return round(number / 100.0, 4) if number > 1 else number
        label = str(value or "").upper()
        return {"LOW": 0.33, "MEDIUM": 0.66, "HIGH": 1.0}.get(label)

    def fetch_keywords(self, target_domain: str, seed_keywords: Optional[List[str]] = None) -> KeywordFetchResult:
        """Live search volume and CPC. Unconfigured and failed calls are not MEASURED."""
        clean_domain = target_domain.replace("https://", "").replace("http://", "").split("/")[0]
        seeds = self._seeds(clean_domain, seed_keywords)
        if not self._connected:
            logger.info("[DataForSEO] Unconnected. Refusing keyword metrics for %s.", clean_domain)
            return KeywordFetchResult(
                domain=clean_domain,
                connected=False,
                provenance=MetricProvenanceState.NOT_CONNECTED,
                keywords=[],
                status_notice="Keywords provider unconnected. Configure DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD.",
            )
        try:
            task = self._post(
                "/v3/keywords_data/google_ads/search_volume/live",
                [{"keywords": seeds[:20], "location_code": 2840, "language_code": "en"}],
            )
        except Exception as exc:
            logger.warning("[DataForSEO] Keyword query failed for %s: %s", clean_domain, exc)
            return KeywordFetchResult(
                domain=clean_domain,
                connected=True,
                provenance=MetricProvenanceState.FAILED,
                keywords=[],
                status_notice=f"DataForSEO keyword query failed: {exc}",
            )
        keywords: List[KeywordMetric] = []
        for row in task.get("result") or []:
            if not isinstance(row, dict) or not row.get("keyword"):
                continue
            volume = row.get("search_volume")
            cpc = row.get("cpc")
            keywords.append(KeywordMetric(
                keyword=str(row["keyword"]),
                search_volume=int(volume) if isinstance(volume, (int, float)) else None,
                cpc_usd=float(cpc) if isinstance(cpc, (int, float)) else None,
                competition=self._competition_ratio(row.get("competition_index") if row.get("competition_index") is not None else row.get("competition")),
                keyword_difficulty=int(row["keyword_difficulty"]) if isinstance(row.get("keyword_difficulty"), (int, float)) else None,
                serp_features=[str(item) for item in (row.get("serp_features") or []) if item],
                provenance=MetricProvenanceState.MEASURED,
            ))
        return KeywordFetchResult(
            domain=clean_domain,
            connected=True,
            provenance=MetricProvenanceState.MEASURED,
            keywords=keywords,
            status_notice="Live keyword metrics from DataForSEO Google Ads search volume.",
        )

    def fetch_backlink_profile(self, target_domain: str) -> BacklinkProfileSummary:
        """Fetches referring domains and link counts. Does not invent domain rating."""
        clean_domain = target_domain.replace("https://", "").replace("http://", "").split("/")[0]
        if not self._connected:
            return BacklinkProfileSummary(
                domain=clean_domain,
                connected=False,
                provenance=MetricProvenanceState.NOT_CONNECTED,
                top_referring_tlds=[],
                status_notice="Backlink index unconnected. Configure DataForSEO credentials. On-page trust is still evaluated from crawl evidence (HTTPS, schema, NAP).",
                source="unconnected_notice",
            )
        try:
            task = self._post(
                "/v3/backlinks/summary/live",
                [{"target": clean_domain, "internal_list_limit": 10, "include_subdomains": True}],
            )
        except Exception as exc:
            logger.warning("[DataForSEO] Backlink query failed for %s: %s", clean_domain, exc)
            return BacklinkProfileSummary(
                domain=clean_domain,
                connected=True,
                provenance=MetricProvenanceState.FAILED,
                top_referring_tlds=[],
                status_notice=f"DataForSEO backlink query failed: {exc}",
                source="dataforseo_live_api",
            )
        rows = task.get("result") or []
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        referring = row.get("referring_domains")
        backlinks = row.get("backlinks")
        return BacklinkProfileSummary(
            domain=clean_domain,
            connected=True,
            provenance=MetricProvenanceState.MEASURED,
            referring_domains=int(referring) if isinstance(referring, (int, float)) else None,
            total_backlinks=int(backlinks) if isinstance(backlinks, (int, float)) else None,
            top_referring_tlds=[],
            status_notice="Live backlink summary from DataForSEO. Domain rating, trust flow, and citation flow are not returned by this endpoint.",
            source="dataforseo_live_api",
        )


dataforseo_provider = KeywordAndBacklinkProvider()
