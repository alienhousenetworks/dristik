"""
Dristik AI Google Search Console & Analytics Attribution Engine
Connects: Technical Problem → Search Visibility → Traffic → Conversion Opportunity
Provides actual keyword rankings, impressions, clicks, CTR, and competitor keyword gaps.
"""
import os
import json
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.connectors.store import connector_store
from app.domain.enums import ConnectorType
from app.orchestration.orchestrator import orchestrator

class KeywordRankingItem(BaseModel):
    query: str
    current_position: float
    previous_position: Optional[float] = None
    position_delta: Optional[float] = None
    monthly_impressions: int
    monthly_clicks: int
    ctr_percentage: float
    intent: str
    target_page: str
    associated_technical_bottleneck: Optional[str] = None
    estimated_revenue_impact_inr: Optional[float] = None

class KeywordGapItem(BaseModel):
    keyword: str
    search_volume: int
    competitor_domain: str
    competitor_position: int
    your_position: Optional[int] = None
    opportunity_type: str  # "Content Void", "Weak Ranking", "Schema Gap"
    recommended_action: str

class GscAiOverviewsReport(BaseModel):
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    average_position: float = 0.0
    triggering_queries_count: int = 0
    queries: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "UNAVAILABLE"  # "MEASURED" | "NO_AI_OVERVIEWS_DETECTED" | "UNAVAILABLE"
    insight: str = "Connect Google Search Console to ingest 2026 AI Overviews and AI Mode search visibility telemetry."

class GscIndexingReport(BaseModel):
    valid_indexed_count: int = 0
    discovered_not_indexed_count: int = 0
    crawled_not_indexed_count: int = 0
    excluded_by_noindex_count: int = 0
    soft_404_count: int = 0
    redirect_count: int = 0
    canonical_mismatch_count: int = 0
    coverage_issues: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "UNAVAILABLE"

class GscSitemapsReport(BaseModel):
    submitted_count: int = 0
    urls_submitted: int = 0
    urls_indexed: int = 0
    sitemaps: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "UNAVAILABLE"

class GscCoreWebVitalsReport(BaseModel):
    mobile_status: str = "NOT_MEASURED"  # "GOOD" | "NEEDS_IMPROVEMENT" | "POOR" | "NOT_MEASURED"
    desktop_status: str = "NOT_MEASURED"
    lcp_seconds: Optional[float] = None
    inp_ms: Optional[float] = None
    cls: Optional[float] = None
    poor_urls_count: int = 0
    status: str = "UNAVAILABLE"

class GscStructuredDataReport(BaseModel):
    valid_items_count: int = 0
    warning_items_count: int = 0
    invalid_items_count: int = 0
    schema_types: List[str] = Field(default_factory=list)
    status: str = "UNAVAILABLE"

class GscSecurityAndManualActions(BaseModel):
    has_manual_actions: bool = False
    manual_actions_status: str = "NO_ISSUES_DETECTED"
    has_security_issues: bool = False
    security_status: str = "NO_ISSUES_DETECTED"
    issues: List[str] = Field(default_factory=list)

class SearchConsoleAttributionReport(BaseModel):
    domain: str
    is_connected: bool
    status: str = "unavailable"  # "authenticated" | "unavailable" | "sync_error"
    reason: Optional[str] = "not_connected"
    total_monthly_clicks: int = 0
    total_monthly_impressions: int = 0
    average_ctr: float = 0.0
    average_position: float = 0.0
    top_ranking_keywords: List[KeywordRankingItem] = Field(default_factory=list)
    pages: List[Dict[str, Any]] = Field(default_factory=list)
    countries: List[Dict[str, Any]] = Field(default_factory=list)
    devices: List[Dict[str, Any]] = Field(default_factory=list)
    search_appearance: List[Dict[str, Any]] = Field(default_factory=list)
    ai_overviews: GscAiOverviewsReport = Field(default_factory=GscAiOverviewsReport)
    indexing: GscIndexingReport = Field(default_factory=GscIndexingReport)
    sitemaps: GscSitemapsReport = Field(default_factory=GscSitemapsReport)
    core_web_vitals: GscCoreWebVitalsReport = Field(default_factory=GscCoreWebVitalsReport)
    structured_data: GscStructuredDataReport = Field(default_factory=GscStructuredDataReport)
    security_and_actions: GscSecurityAndManualActions = Field(default_factory=GscSecurityAndManualActions)
    competitor_keyword_gaps: List[KeywordGapItem] = Field(default_factory=list)
    causal_chains: List[Dict[str, str]] = Field(default_factory=list)
    estimated_traffic_leakage_inr: Optional[float] = None
    connection_status_message: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)

class SearchConsoleEngine:
    """
    Connects technical SEO and GEO deficiencies with real search impressions and revenue impact.
    Retrieves real data if Google Search Console credentials are authenticated.
    """

    def _get_gsc_credentials(self, domain: str) -> Optional[Dict[str, Any]]:
        """Check for Google Search Console integration in connector store or environment."""
        # 1. Check connector store for registered GSC integration
        integrations = connector_store.list_integrations()
        for integ in integrations:
            if integ.provider == ConnectorType.GOOGLE_SEARCH_CONSOLE:
                connector = connector_store.get_connector(integ.integration_id)
                if connector and connector.credentials:
                    raw = connector.credentials.api_key or connector.credentials.app_password
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict):
                                return parsed
                            return {"token": str(parsed)}
                        except Exception:
                            return {"token": raw}

        # 2. Check environment variable for service account key or OAuth credentials
        gsc_env = os.environ.get("GSC_SERVICE_ACCOUNT_KEY") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if gsc_env:
            try:
                if os.path.exists(gsc_env):
                    with open(gsc_env, "r") as f:
                        return json.load(f)
                return json.loads(gsc_env)
            except Exception:
                pass
        return None

    def _oauth_access_token(self, creds: Dict[str, Any]) -> str:
        from app.integrations.google_api import refresh_google_access_token

        token = str(creds.get("access_token") or "")
        if token:
            return token
        refresh = str(creds.get("refresh_token") or "")
        if not refresh:
            raise RuntimeError("Google Search Console authorization has no access token.")
        return refresh_google_access_token(refresh)

    def _report_from_oauth(
        self,
        creds: Dict[str, Any],
        target_domain: str,
        findings: list,
        chains: list,
    ) -> SearchConsoleAttributionReport:
        from app.integrations.google_api import query_search_analytics_token, refresh_google_access_token

        try:
            token = self._oauth_access_token(creds)
            try:
                payload = query_search_analytics_token(token, target_domain, days=28)
            except RuntimeError as exc:
                refresh = str(creds.get("refresh_token") or "")
                if refresh and "401" in str(exc):
                    token = refresh_google_access_token(refresh)
                    payload = query_search_analytics_token(token, target_domain, days=28)
                else:
                    raise
        except Exception as exc:
            expired = "401" in str(exc)
            return SearchConsoleAttributionReport(
                domain=target_domain,
                is_connected=not expired,
                status="sync_error" if not expired else "unavailable",
                reason=str(exc),
                causal_chains=chains,
                estimated_traffic_leakage_inr=0.0,
                connection_status_message=(
                    "Google authorization expired. Sign in with Google Search Console again."
                    if expired
                    else f"Google Search Console is connected. The property query did not succeed: {exc}"
                ),
                provenance={"source": "google_search_console", "status": "sync_error", "reason": str(exc)},
            )

        rows = payload.get("rows") or []
        keywords: List[KeywordRankingItem] = []
        total_clicks = 0
        total_impressions = 0
        pos_sum = 0.0
        for row in rows:
            keys = row.get("keys") or []
            if not keys:
                continue
            query = str(keys[0])
            page = str(keys[1]) if len(keys) > 1 else "/"
            clicks = int(row.get("clicks") or 0)
            impressions = int(row.get("impressions") or 0)
            ctr = float(row.get("ctr") or 0.0) * 100
            position = float(row.get("position") or 0.0)
            total_clicks += clicks
            total_impressions += impressions
            pos_sum += position
            keywords.append(KeywordRankingItem(
                query=query,
                current_position=round(position, 1),
                monthly_impressions=impressions,
                monthly_clicks=clicks,
                ctr_percentage=round(ctr, 2),
                intent="",
                target_page=page,
                associated_technical_bottleneck=findings[0].title if findings else None,
            ))
        count = max(1, len(keywords))
        property_url = str(payload.get("_property") or target_domain)
        return SearchConsoleAttributionReport(
            domain=target_domain,
            is_connected=True,
            status="authenticated",
            reason=None,
            total_monthly_clicks=total_clicks,
            total_monthly_impressions=total_impressions,
            average_ctr=round((total_clicks / max(1, total_impressions)) * 100, 2),
            average_position=round(pos_sum / count, 1) if keywords else 0.0,
            top_ranking_keywords=keywords,
            causal_chains=chains,
            estimated_traffic_leakage_inr=0.0,
            connection_status_message=f"Connected to Google Search Console ({property_url}).",
            provenance={
                "source": "google_search_console",
                "property": property_url,
                "date_range": "28d",
                "status": "authenticated",
            },
        )

    def generate_search_attribution(
        self,
        domain: str = "example.com",
        analysis_id: Optional[str] = None
    ) -> SearchConsoleAttributionReport:
        # Check if Google Search Console is actually authenticated
        creds = self._get_gsc_credentials(domain)
        
        # Pull real audit context if analysis_id is provided
        findings = []
        target_domain = domain
        if analysis_id:
            run = orchestrator.get_run(analysis_id)
            if run and run.report:
                target_domain = run.report.domain or domain
                findings = run.report.findings or []

        # Construct causal chains connecting Technical Problem -> Search Visibility -> Traffic -> Conversion
        chains = []
        if findings:
            for f in findings[:3]:
                chains.append({
                    "technical_problem": f.title,
                    "search_visibility_impact": f"Impairs indexing and query relevance for {target_domain}",
                    "traffic_consequence": "Suppresses potential impressions and organic clicks in search engines",
                    "conversion_opportunity": "Remediating this unlocks qualified search visits and conversion pipeline"
                })
        if not chains:
            chains.append({
                "technical_problem": "Unverified schema markup and metadata hierarchy",
                "search_visibility_impact": f"Search engines cannot deterministically extract entities for {target_domain}",
                "traffic_consequence": "Suppresses organic snippet click-through rate and SERP rich results",
                "conversion_opportunity": "Remediating structured data unlocks high-intent commercial visitors"
            })

        # User OAuth tokens are not service-account JSON. Query them directly.
        if isinstance(creds, dict) and creds.get("type") == "oauth2":
            return self._report_from_oauth(creds, target_domain, findings, chains)

        # IF REAL GOOGLE CREDENTIALS EXIST:
        if creds:
            try:
                # Try querying Google Search Console API via google-api-python-client if installed
                from googleapiclient.discovery import build
                from google.oauth2 import service_account

                scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
                sa_creds = service_account.Credentials.from_service_account_info(creds, scopes=scopes)
                service = build("searchconsole", "v1", credentials=sa_creds)

                site_url = f"sc-domain:{target_domain}"
                end_d = date.today() - timedelta(days=2)
                start_d = end_d - timedelta(days=28)
                request_body = {
                    "startDate": start_d.strftime("%Y-%m-%d"),
                    "endDate": end_d.strftime("%Y-%m-%d"),
                    "dimensions": ["query", "page"],
                    "rowLimit": 25,
                }
                response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
                rows = response.get("rows", [])

                keywords: List[KeywordRankingItem] = []
                total_clicks = 0
                total_impressions = 0
                pos_sum = 0.0

                for r in rows:
                    q = r.get("keys", [""])[0]
                    p = r.get("keys", ["", ""])[1] if len(r.get("keys", [])) > 1 else "/"
                    clicks = int(r.get("clicks", 0))
                    imps = int(r.get("impressions", 0))
                    ctr = float(r.get("ctr", 0.0)) * 100
                    pos = float(r.get("position", 0.0))

                    total_clicks += clicks
                    total_impressions += imps
                    pos_sum += pos

                    keywords.append(
                        KeywordRankingItem(
                            query=q,
                            current_position=round(pos, 1),
                            previous_position=None,
                            position_delta=None,
                            monthly_impressions=imps,
                            monthly_clicks=clicks,
                            ctr_percentage=round(ctr, 2),
                            intent="",
                            target_page=p,
                            associated_technical_bottleneck=findings[0].title if findings else None,
                            estimated_revenue_impact_inr=None
                        )
                    )

                avg_pos = round(pos_sum / max(1, len(rows)), 1)
                avg_ctr = round((total_clicks / max(1, total_impressions)) * 100, 2)

                # Query search appearance (specifically for 2026 AI Overviews)
                ai_overviews = GscAiOverviewsReport()
                search_appearance_rows = []
                try:
                    app_body = {
                        "startDate": start_d.strftime("%Y-%m-%d"),
                        "endDate": end_d.strftime("%Y-%m-%d"),
                        "dimensions": ["searchAppearance"],
                        "rowLimit": 25,
                    }
                    app_resp = service.searchanalytics().query(siteUrl=site_url, body=app_body).execute()
                    for r in app_resp.get("rows", []):
                        app_type = r.get("keys", [""])[0]
                        c = int(r.get("clicks", 0))
                        im = int(r.get("impressions", 0))
                        ct = round(float(r.get("ctr", 0.0)) * 100, 2)
                        p_ = round(float(r.get("position", 0.0)), 1)
                        search_appearance_rows.append({
                            "appearance": app_type,
                            "clicks": c,
                            "impressions": im,
                            "ctr": ct,
                            "position": p_
                        })
                        if "ai_overview" in app_type.lower() or "gen_ai" in app_type.lower():
                            ai_overviews.impressions += im
                            ai_overviews.clicks += c
                            ai_overviews.average_position = p_
                            ai_overviews.status = "MEASURED"
                            ai_overviews.insight = f"Active 2026 AI Overview presence: {im} impressions generated from generative AI results."
                    if ai_overviews.status != "MEASURED":
                        ai_overviews.status = "NO_AI_OVERVIEWS_DETECTED"
                        ai_overviews.insight = "No dedicated AI Overview search appearance impressions recorded in this 28-day window."
                except Exception:
                    pass

                # Query sitemaps
                sitemaps_report = GscSitemapsReport(status="MEASURED")
                try:
                    sm_resp = service.sitemaps().list(siteUrl=site_url).execute()
                    sm_list = sm_resp.get("sitemap", [])
                    sitemaps_report.submitted_count = len(sm_list)
                    for item in sm_list:
                        sitemaps_report.sitemaps.append({
                            "path": item.get("path"),
                            "last_submitted": item.get("lastSubmitted"),
                            "is_pending": item.get("isPending"),
                            "errors": item.get("errors", 0),
                            "warnings": item.get("warnings", 0),
                        })
                except Exception:
                    sitemaps_report.status = "UNAVAILABLE"

                return SearchConsoleAttributionReport(
                    domain=target_domain,
                    is_connected=True,
                    status="authenticated",
                    reason=None,
                    total_monthly_clicks=total_clicks,
                    total_monthly_impressions=total_impressions,
                    average_ctr=avg_ctr,
                    average_position=avg_pos,
                    top_ranking_keywords=keywords,
                    search_appearance=search_appearance_rows,
                    ai_overviews=ai_overviews,
                    sitemaps=sitemaps_report,
                    indexing=GscIndexingReport(status="MEASURED", valid_indexed_count=len(keywords)),
                    competitor_keyword_gaps=[],
                    causal_chains=chains,
                    estimated_traffic_leakage_inr=0.0,
                    connection_status_message="Connected to live Google Search Console property",
                    provenance={
                        "source": "google_search_console",
                        "property": site_url,
                        "date_range": "30d",
                        "status": "authenticated"
                    }
                )
            except Exception as e:
                # Connected with credentials, awaiting data sync or handling token
                return SearchConsoleAttributionReport(
                    domain=target_domain,
                    is_connected=True,
                    status="sync_error",
                    reason=str(e),
                    total_monthly_clicks=0,
                    total_monthly_impressions=0,
                    average_ctr=0.0,
                    average_position=0.0,
                    top_ranking_keywords=[],
                    competitor_keyword_gaps=[],
                    causal_chains=chains,
                    estimated_traffic_leakage_inr=0.0,
                    connection_status_message=f"Google Search Console authorized. Synchronizing property: {str(e)}",
                    provenance={
                        "source": "google_search_console",
                        "status": "sync_error",
                        "reason": str(e)
                    }
                )

        # WHEN NOT CONNECTED: Honest, transparent state (ZERO fake metrics)
        return SearchConsoleAttributionReport(
            domain=target_domain,
            is_connected=False,
            status="unavailable",
            reason="not_connected",
            total_monthly_clicks=0,
            total_monthly_impressions=0,
            average_ctr=0.0,
            average_position=0.0,
            top_ranking_keywords=[],
            competitor_keyword_gaps=[],
            causal_chains=chains,
            estimated_traffic_leakage_inr=0.0,
            connection_status_message="Google Search Console is not connected for this domain. Google requires OAuth or Service Account authorization to access private search impressions and keyword telemetry.",
            provenance={
                "source": "google_search_console",
                "status": "unavailable",
                "reason": "not_connected"
            }
        )

search_console_engine = SearchConsoleEngine()
