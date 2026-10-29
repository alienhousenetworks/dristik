"""
Integrations API Routes
Manages first-party Google Search Console, Google Analytics 4, and external keyword index providers.
Fail-closed authentication and zero synthetic fallbacks.
"""
import os
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional
from app.integrations.google_connectors import (
    gsc_connector,
    ga4_connector,
    GscPerformanceSummary,
    Ga4PerformanceSummary,
)
from app.domain.enums import MetricProvenanceState

router = APIRouter(
    prefix="/integrations",
    tags=["First-Party Analytics & External Connectors"],
    dependencies=[Depends(get_current_user_optional)],
)


class Ga4ConnectRequest(BaseModel):
    property_id: str


class GscConnectRequest(BaseModel):
    credentials_json_path: Optional[str] = None
    service_account_email: Optional[str] = None


@router.get("/status")
def get_integrations_status(user: Optional[UserIdentity] = Depends(get_current_user_optional)) -> Dict[str, Any]:
    """Returns provider status for the signed-in organization."""
    from app.connectors.store import connector_store
    from app.domain.enums import ConnectorType, ConnectorHealthStatus

    org_id = user.org_id if user else "org_default"
    integrations = connector_store.list_integrations(org_id)
    ga4_integ = [i for i in integrations if i.provider == ConnectorType.GOOGLE_ANALYTICS_4]
    ga4_connected = any(i.status == ConnectorHealthStatus.CONNECTED for i in ga4_integ)
    ga4_prop = None
    for integration in ga4_integ:
        property_id = (integration.settings or {}).get("property_id")
        if property_id:
            ga4_prop = property_id
            break

    gsc_integ = [i for i in integrations if i.provider == ConnectorType.GOOGLE_SEARCH_CONSOLE]
    gsc_connected = any(i.status == ConnectorHealthStatus.CONNECTED for i in gsc_integ)

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
def connect_ga4(payload: Ga4ConnectRequest, user: Optional[UserIdentity] = Depends(get_current_user_optional)):
    """Configures GA4 property ID with format verification across OAuth, service account, and environment credentials."""
    if not payload.property_id or not payload.property_id.strip():
        raise HTTPException(status_code=400, detail="property_id is required")
    clean_prop = payload.property_id.strip()
    if not ga4_connector.verify_property_id(clean_prop):
        raise HTTPException(
            status_code=400,
            detail="Invalid GA4 property ID format. Must be numeric ID (e.g. 123456789) or properties/123456789"
        )

    from app.connectors.store import connector_store
    from app.domain.enums import ConnectorType, ConnectorHealthStatus
    from app.integrations.google_api import query_ga4_with_token, query_ga4, refresh_google_access_token

    org_id = user.org_id if user else "org_default"
    integrations = connector_store.list_integrations(org_id)
    ga4_integs = [i for i in integrations if i.provider in (ConnectorType.GOOGLE_ANALYTICS_4, ConnectorType.GOOGLE_ANALYTICS)]

    probe_success = False
    error_msg = None

    if ga4_integs:
        for integ in ga4_integs:
            connector = connector_store.get_connector(integ.integration_id)
            creds = getattr(connector, "credentials", None)
            raw = getattr(creds, "api_key", None) or getattr(creds, "app_password", None) or ""
            parsed = {}
            if raw:
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    parsed = {}
            if isinstance(parsed, dict) and (parsed.get("access_token") or parsed.get("refresh_token")):
                token = parsed.get("access_token")
                refresh = parsed.get("refresh_token")
                try:
                    query_ga4_with_token(token, clean_prop)
                    probe_success = True
                except Exception as exc:
                    if refresh and ("401" in str(exc) or "expired" in str(exc).lower()):
                        try:
                            token = refresh_google_access_token(refresh)
                            query_ga4_with_token(token, clean_prop)
                            probe_success = True
                            parsed["access_token"] = token
                        except Exception as ref_exc:
                            error_msg = str(ref_exc)
                    else:
                        error_msg = str(exc)
                if probe_success:
                    parsed["property_id"] = clean_prop
                    if creds:
                        creds.api_key = json.dumps(parsed)
                    integ.settings = integ.settings or {}
                    integ.settings["property_id"] = clean_prop
                    integ.status = ConnectorHealthStatus.CONNECTED
                    connector_store.persist(integ)
                    break
            elif isinstance(parsed, dict) and parsed.get("type") == "service_account":
                try:
                    query_ga4(parsed, clean_prop)
                    probe_success = True
                    parsed["property_id"] = clean_prop
                    if creds:
                        creds.api_key = json.dumps(parsed)
                    integ.settings = integ.settings or {}
                    integ.settings["property_id"] = clean_prop
                    integ.status = ConnectorHealthStatus.CONNECTED
                    connector_store.persist(integ)
                    break
                except Exception as exc:
                    error_msg = str(exc)

    if not probe_success:
        credentials_path = ga4_connector.credentials_path()
        if credentials_path and ga4_connector.verify_credentials(credentials_path):
            try:
                query_ga4(credentials_path, clean_prop)
                probe_success = True
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"GA4 Data API probe failed: {exc}")
        elif error_msg:
            raise HTTPException(status_code=400, detail=f"GA4 Data API probe failed: {error_msg}")
        else:
            raise HTTPException(
                status_code=400,
                detail="GA4 requires Google OAuth authorization or a Google Service Account key. Please click 'Sign in with Google' or upload your service account credentials.",
            )

    ga4_connector.property_id = clean_prop
    ga4_connector._connected = True
    return {
        "status": "authenticated",
        "property_id": ga4_connector.property_id,
        "provenance": MetricProvenanceState.MEASURED,
        "detail": "GA4 Data API probe succeeded and property connected.",
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

    from app.connectors.store import connector_store

    stored_key = None
    for integration in connector_store.list_integrations():
        status = getattr(integration.status, "value", integration.status)
        if integration.provider == ConnectorType.CRUX and str(status).lower() == "connected":
            live = connector_store.get_connector(integration.integration_id)
            candidate = live.credentials.api_key if live and live.credentials else None
            if candidate and str(candidate).strip():
                stored_key = str(candidate).strip()
                break
    connector = CruxConnector(ConnectorCredentials(provider=ConnectorType.CRUX, api_key=stored_key))
    res = await connector.fetch_telemetry(domain)
    return res.model_dump()
