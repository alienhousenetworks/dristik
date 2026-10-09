"""
Integrations API Routes
Manages first-party Google Search Console, Google Analytics 4, and external keyword index providers.
Fail-closed authentication and zero synthetic fallbacks.
"""
import os
from fastapi import APIRouter, Query, Body, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.integrations.google_connectors import (
    gsc_connector,
    ga4_connector,
    GscPerformanceSummary,
    Ga4PerformanceSummary,
)
from app.domain.enums import MetricProvenanceState

router = APIRouter(prefix="/integrations", tags=["First-Party Analytics & External Connectors"])


class Ga4ConnectRequest(BaseModel):
    property_id: str


class GscConnectRequest(BaseModel):
    credentials_json_path: Optional[str] = None
    service_account_email: Optional[str] = None


@router.get("/status")
def get_integrations_status() -> Dict[str, Any]:
    """Returns the operational and connection status of all analytics and keyword providers."""
    from app.connectors.store import connector_store
    from app.domain.enums import ConnectorType, ConnectorHealthStatus

    integrations = connector_store.list_integrations()
    ga4_integ = [i for i in integrations if i.provider == ConnectorType.GOOGLE_ANALYTICS_4]
    ga4_connected = bool(ga4_connector.is_connected or any(i.status == ConnectorHealthStatus.CONNECTED for i in ga4_integ))
    ga4_prop = ga4_connector.property_id
    if not ga4_prop and ga4_integ:
        for i in ga4_integ:
            p = i.settings.get("property_id")
            if p:
                ga4_prop = p
                break

    gsc_integ = [i for i in integrations if i.provider == ConnectorType.GOOGLE_SEARCH_CONSOLE]
    gsc_connected = bool(gsc_connector.is_connected or any(i.status == ConnectorHealthStatus.CONNECTED for i in gsc_integ))

    return {
        "google_search_console": {
            "connected": gsc_connected,
            "provider": "Google Search Console API v1",
            "capabilities": ["real_search_queries", "impressions", "clicks", "average_position", "crawl_coverage"],
        },
        "google_analytics_4": {
            "connected": ga4_connected,
            "property_id": ga4_prop,
            "provider": "Google Analytics 4 Data API",
            "capabilities": ["real_sessions", "bounce_rate", "dwell_time", "conversion_rate", "landing_pages"],
        },
        "dataforseo_keyword_index": {
            "connected": bool(
                (settings.DATAFORSEO_LOGIN or os.getenv("DATAFORSEO_LOGIN"))
                and (settings.DATAFORSEO_PASSWORD or os.getenv("DATAFORSEO_PASSWORD"))
            ),
            "provider": "DataForSEO Live SERP & Backlink API",
            "capabilities": ["search_volume", "keyword_difficulty", "cpc", "referring_domains", "backlink_count"],
        },
        "ahrefs": {
            "connected": bool(settings.AHREFS_API_KEY or (settings.AHREFS_CLIENT_ID and settings.AHREFS_CLIENT_SECRET)),
            "provider": "Ahrefs API v3",
            "capabilities": ["referring_domains", "domain_rating", "backlink_growth", "anchor_distribution"],
        },
        "semrush": {
            "connected": bool(settings.SEMRUSH_API_KEY or (settings.SEMRUSH_CLIENT_ID and settings.SEMRUSH_CLIENT_SECRET)),
            "provider": "Semrush Authority & Backlinks API",
            "capabilities": ["authority_score", "referring_domains", "toxic_backlinks", "keyword_trends"],
        },
        "majestic": {
            "connected": bool(settings.MAJESTIC_API_KEY),
            "provider": "Majestic SEO Flow Metrics",
            "capabilities": ["trust_flow", "citation_flow", "topical_trust", "referring_subnets"],
        },
        "google_business_profile": {
            "connected": bool(os.getenv("GBP_ACCOUNT_ID") or os.getenv("GOOGLE_BUSINESS_PROFILE_ID")),
            "provider": "Google Business Profile API",
            "capabilities": ["local_reviews", "rating_aggregation", "business_attributes", "local_search_impressions"],
        },
        "brand_mentions": {
            "connected": bool(settings.BRAND_MENTIONS_ENABLED and (settings.BRAND_MENTIONS_API_KEY or settings.BRAND_MENTIONS_PROVIDER)),
            "provider": settings.BRAND_MENTIONS_PROVIDER or "Brand Entity Tracker",
            "capabilities": ["unlinked_mentions", "sentiment_analysis", "co_citation_volume"],
        },
        "citations_directories": {
            "connected": bool(settings.CITATIONS_ENABLED and (settings.CITATIONS_API_KEY or settings.CITATIONS_PROVIDER)),
            "provider": settings.CITATIONS_PROVIDER or "Directory & Citation Aggregator",
            "capabilities": ["nap_consistency", "business_directory_citations", "local_directory_listing"],
        },
    }


@router.get("/gsc/performance", response_model=GscPerformanceSummary)
def get_gsc_performance(
    domain: str = Query(..., description="Target domain to inspect GSC search performance for"),
    days: int = Query(90, description="Date window in days")
):
    """Fetches real Google Search Console queries, clicks, impressions, and crawl coverage."""
    return gsc_connector.fetch_performance(domain, days=days)


@router.get("/ga4/performance", response_model=Ga4PerformanceSummary)
def get_ga4_performance(
    domain: str = Query(..., description="Target domain to inspect GA4 conversion metrics for")
):
    """Fetches real Google Analytics 4 bounce rates, sessions, and conversion funnels."""
    return ga4_connector.fetch_performance(domain)


@router.post("/gsc/connect")
def connect_gsc(payload: GscConnectRequest):
    """Configures Google Search Console connection with verification."""
    if not payload.credentials_json_path or not payload.credentials_json_path.strip():
        raise HTTPException(
            status_code=400,
            detail="credentials_json_path is required to authenticate Google Search Console"
        )
    clean_path = payload.credentials_json_path.strip()
    if not gsc_connector.verify_credentials(clean_path):
        raise HTTPException(
            status_code=400,
            detail=f"Google Search Console credentials file invalid or unreachable at '{clean_path}'"
        )
    try:
        from app.integrations.google_api import service_account_access_token
        service_account_access_token(clean_path, ["https://www.googleapis.com/auth/webmasters.readonly"])
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Google Search Console credentials did not authenticate: {exc}",
        )
    gsc_connector.credentials_json = clean_path
    gsc_connector._connected = True
    return {
        "status": "authenticated",
        "provider": "Google Search Console",
        "provenance": MetricProvenanceState.NOT_CONFIGURED,
        "detail": "Service account authenticated. Search metrics are measured only when a property query succeeds.",
    }


@router.post("/ga4/connect")
def connect_ga4(payload: Ga4ConnectRequest):
    """Configures GA4 property ID with format verification."""
    if not payload.property_id or not payload.property_id.strip():
        raise HTTPException(status_code=400, detail="property_id is required")
    clean_prop = payload.property_id.strip()
    if not ga4_connector.verify_property_id(clean_prop):
        raise HTTPException(
            status_code=400,
            detail="Invalid GA4 property ID format. Must be numeric ID (e.g. 123456789) or properties/123456789"
        )
    credentials_path = ga4_connector.credentials_path()
    if not credentials_path or not ga4_connector.verify_credentials(credentials_path):
        raise HTTPException(
            status_code=400,
            detail="GA4 requires GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account JSON. A property ID alone is not a connection.",
        )
    try:
        from app.integrations.google_api import query_ga4
        query_ga4(credentials_path, clean_prop)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"GA4 Data API probe failed: {exc}")
    ga4_connector.property_id = clean_prop
    ga4_connector._connected = True
    return {
        "status": "authenticated",
        "property_id": ga4_connector.property_id,
        "provenance": MetricProvenanceState.MEASURED,
        "detail": "GA4 Data API probe succeeded.",
    }


@router.get("/keywords")
def get_keywords(domain: str = Query(..., description="Target domain to inspect keyword metrics for")):
    """Fetches search volume, CPC, and keyword difficulty."""
    from app.integrations.dataforseo_provider import dataforseo_provider
    result = dataforseo_provider.fetch_keywords(domain)
    return result.model_dump()


@router.get("/backlinks")
def get_backlinks(domain: str = Query(..., description="Target domain to inspect backlink profile for")):
    """Fetches referring domains, backlinks, and link graph status."""
    from app.integrations.dataforseo_provider import dataforseo_provider
    return dataforseo_provider.fetch_backlink_profile(domain).model_dump()


@router.get("/telemetry/{domain}")
async def get_domain_telemetry(domain: str) -> Dict[str, Any]:
    """
    Unified telemetry endpoint polling GSC, GA4, CrUX, and External SEO providers.
    Enforces clean fail-closed status tags and zero synthetic metric fabrication.
    """
    from app.connectors.store import connector_store
    telemetry_svc = connector_store.get_telemetry_service()
    package = await telemetry_svc.fetch_all_telemetry(domain)
    return package.model_dump()


@router.get("/crux/{domain}")
async def get_crux_telemetry(domain: str) -> Dict[str, Any]:
    """
    Queries Google CrUX origin Core Web Vitals (p75 LCP, INP, CLS, FCP).
    Returns explicit lab_fallback_only when domain has insufficient CrUX dataset traffic.
    """
    from app.connectors.crux.connector import CruxConnector
    from app.connectors.base.models import ConnectorCredentials
    from app.domain.enums import ConnectorType

    connector = CruxConnector(ConnectorCredentials(provider=ConnectorType.CRUX))
    res = await connector.fetch_telemetry(domain)
    return res.model_dump()
