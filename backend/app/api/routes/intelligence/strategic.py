"""
Dristik AI Strategic Intelligence API Routes
Exposes Competitor Discovery, Search Console Attribution, Real AI Citation Tracking,
Commercial Lead-Gen Opportunities, and Agency Multi-Client Workspaces.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.identity.access import require_analysis
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user, get_current_user_optional

from app.intelligence.competitive.discovery import competitor_discovery_engine, CompetitorBenchmarkMatrix
from app.intelligence.competitive.resolution.rejection_store import rejection_store
from app.intelligence.competitive.benchmark import (
    competitor_benchmark_engine,
    CompetitiveBenchmarkResult,
    CompetitorPillarScores,
)
from app.intelligence.competitive.engine import competitive_intelligence_engine
from app.intelligence.competitive.models import DristikCompetitiveReport
from app.intelligence.business.search_console import search_console_engine, SearchConsoleAttributionReport
from app.intelligence.citations.tracker import ai_citation_tracker, AiCitationTrackingDashboard
from app.intelligence.geo.benchmark_runner import benchmark_runner, GeoBenchmarkReport
from app.intelligence.business.lead_gen import lead_gen_engine, CommercialOpportunity
from app.tenancy.agency import agency_manager, AgencyWorkspaceSummary, AgencyClientAccount
router = APIRouter(prefix="/intelligence", tags=["Strategic Commercial Intelligence"])


def _owned_analysis(analysis_id: Optional[str], user: Optional[UserIdentity]):
    """Load a stored audit only for the organization that owns it."""
    if not analysis_id:
        return None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return require_analysis(analysis_id, user)

class AddAgencyClientRequest(BaseModel):
    client_name: str = Field(..., description="Legal or display name of the client")
    domain: str = Field(..., description="Target domain to manage")

class CompetitorRejectionRequest(BaseModel):
    target_domain: str = Field(..., description="Target website domain")
    rejected_domain: str = Field(..., description="Competitor domain to reject and remember")

@router.get("/competitors", response_model=CompetitorBenchmarkMatrix)
async def get_competitor_benchmark(
    analysis_id: Optional[str] = None,
    website_url: Optional[str] = None,
    competitor_urls: Optional[List[str]] = Query(None),
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Automated Competitor Discovery & 7-Vector Benchmark Matrix.
    Identifies peer-level competitors matching commercial scale and specialization,
    coexisting with user-supplied benchmarks and respecting domain rejections.
    """
    bp = None
    honest_scores = None
    url = website_url
    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report:
            bp = run.report.business_profile
            honest_scores = run.report.honest_scores
            url = run.website_url or url

    if not url:
        raise HTTPException(status_code=400, detail="Either website_url or a valid analysis_id is required.")

    rejected = rejection_store.get_rejected_domains(url)

    return await competitor_discovery_engine.discover_and_benchmark(
        bp,
        url,
        competitor_urls=competitor_urls,
        honest_scores=honest_scores,
        rejected_domains=rejected,
    )

@router.post("/competitors/reject")
async def record_competitor_rejection(req: CompetitorRejectionRequest):
    """Stores rejected competitor domain so it is permanently excluded from future suggestions."""
    rejection_store.record_rejection(req.target_domain, req.rejected_domain)
    return {
        "status": "ok",
        "target_domain": req.target_domain,
        "rejected_domain": req.rejected_domain,
        "message": f"Recorded rejection of {req.rejected_domain} for {req.target_domain}"
    }

@router.get("/competitors/report", response_model=DristikCompetitiveReport)
async def get_unified_competitive_report(
    analysis_id: Optional[str] = None,
    domain: Optional[str] = None,
    competitors: Optional[List[str]] = Query(None),
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Returns the evidence-backed Dristik Competitive Intelligence Report.
    Includes dynamic (X, Y) landscape coordinates, multi-type competitor classification,
    dimensional gaps, causal explainability proofs, and empirical evidence table.
    """
    bp = None
    pages = []
    evals = []
    obs = []
    resolved_domain = domain or ""

    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report:
            # Check cached report first
            if getattr(run.report, "competitive_report", None):
                try:
                    return DristikCompetitiveReport(**run.report.competitive_report)
                except Exception:
                    pass
            bp = run.report.business_profile
            resolved_domain = run.report.domain or resolved_domain
            pages = (run.report.crawl_manifest.pages if run.report.crawl_manifest else [])
            evals = run.report.commercial_evaluations or []
            obs = getattr(run.report, "observatory_records", []) or []

    if not resolved_domain:
        raise HTTPException(status_code=400, detail="Either domain or a valid analysis_id is required.")

    # If competitors not supplied and business_profile has none, auto-discover direct peers
    active_competitors = competitors
    if not active_competitors and (not bp or not getattr(bp, "competitors", None)):
        rejected = rejection_store.get_rejected_domains(resolved_domain)
        disc = await competitor_discovery_engine.discover_and_benchmark(
            business_profile=bp,
            website_url=resolved_domain,
            rejected_domains=rejected,
        )
        if disc and disc.competitors:
            active_competitors = [c.domain for c in disc.competitors if c.domain != resolved_domain][:3]

    return competitive_intelligence_engine.build_competitive_report(
        target_domain=resolved_domain,
        business_profile=bp,
        target_pages=pages,
        competitor_domains=active_competitors,
        commercial_evaluations=evals,
        observatory_records=obs,
        audit_id=analysis_id,
    )

class CompetitiveBenchmarkRequest(BaseModel):
    target_domain: str = Field(..., description="Your target website domain")
    competitor_1_url: str = Field(..., description="First competitor website URL or domain")
    competitor_2_url: str = Field(..., description="Second competitor website URL or domain")
    analysis_id: Optional[str] = Field(None, description="Optional active audit run ID")

@router.post("/competitors/benchmark", response_model=CompetitiveBenchmarkResult)
async def run_live_competitor_benchmark(
    req: CompetitiveBenchmarkRequest,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Live Scrapes 2 Competitor Homepages with the identical CrawlerService pipeline.
    Calculates side-by-side 5-pillar scores, relative ranks, peer average deltas,
    and isolates empirical competitive moats and vulnerability gaps.
    """
    target_ev = None
    target_scores = None

    if req.analysis_id:
        run = _owned_analysis(req.analysis_id, user)
        if run and run.report:
            if run.report.crawl_manifest and run.report.crawl_manifest.pages:
                target_ev = run.report.crawl_manifest.pages[0]

    result = await competitor_benchmark_engine.benchmark_two_competitors(
        target_domain=req.target_domain,
        competitor_1_url=req.competitor_1_url,
        competitor_2_url=req.competitor_2_url,
        target_evidence=target_ev,
        target_scores=target_scores
    )
    return result

@router.get("/competitors/suggestions")
async def get_competitor_suggestions(
    domain: str = Query(..., description="Target domain"),
    niche: Optional[str] = Query(None, description="Industry niche"),
    analysis_id: Optional[str] = Query(None, description="Optional active audit run ID"),
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """Suggests 2-3 direct competitor peers based on domain, business profile, and scale parity."""
    clean = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
    bp = None
    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report:
            bp = run.report.business_profile

    rejected = rejection_store.get_rejected_domains(clean)
    disc = await competitor_discovery_engine.discover_and_benchmark(
        business_profile=bp,
        website_url=clean,
        rejected_domains=rejected,
    )

    suggestions = []
    if disc and disc.competitors:
        for c in disc.competitors:
            if c.domain != clean:
                tier_label = c.scale_tier.title() if c.scale_tier else "Direct"
                suggestions.append({
                    "domain": c.domain,
                    "brand": c.brand_name,
                    "category": f"{tier_label} Peer Studio" if c.scale_tier == "boutique" else f"{tier_label} Peer",
                    "scale_score": c.scale_score,
                })

    if len(suggestions) < 2 and disc and disc.aspirational_competitors:
        for a in disc.aspirational_competitors:
            if a.domain != clean:
                suggestions.append({
                    "domain": a.domain,
                    "brand": a.brand_name,
                    "category": "Aspirational Leader",
                    "scale_score": a.scale_score,
                })

    if len(suggestions) < 2:
        suggestions = [
            {"domain": "thoughtbot.com", "brand": "Thoughtbot", "category": "Product & Engineering Studio", "scale_score": 0.25},
            {"domain": "strv.com", "brand": "STRV", "category": "Digital Engineering Studio", "scale_score": 0.25}
        ]

    return {
        "target": clean,
        "suggestions": suggestions[:3]
    }

@router.get("/search-console", response_model=SearchConsoleAttributionReport)
async def get_search_console_attribution(
    domain: Optional[str] = None,
    analysis_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Google Search Console & Analytics Attribution Report.
    Connects: Technical problem -> Search visibility -> Traffic -> Conversion opportunity.
    """
    if not domain and not analysis_id:
        raise HTTPException(status_code=400, detail="Either domain or analysis_id must be provided.")
    if analysis_id:
        _owned_analysis(analysis_id, user)
    return search_console_engine.generate_search_attribution(domain=domain or "", analysis_id=analysis_id)

@router.get("/ai-citations", response_model=AiCitationTrackingDashboard)
async def get_real_ai_citations(
    domain: Optional[str] = None,
    biz_name: Optional[str] = None,
    niche: Optional[str] = None,
    analysis_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Hero Real AI Citation Tracker.
    Monitors live commercial buyer queries across ChatGPT, Perplexity, Gemini, Google AI, and Claude.
    Records mention status, ranking position, cited URLs, and competitor substitution.
    """
    resolved_domain = domain
    resolved_biz_name = biz_name
    resolved_niche = niche

    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report and run.report.business_profile:
            bp = run.report.business_profile
            resolved_domain = resolved_domain or bp.primary_domain or run.website_url
            resolved_biz_name = resolved_biz_name or bp.business_name
            resolved_niche = resolved_niche or bp.industry

    if not resolved_domain and not resolved_biz_name:
        raise HTTPException(status_code=400, detail="Target domain or business name is required for AI citation tracking.")

    return await ai_citation_tracker.track_buyer_queries(
        domain=resolved_domain or "",
        biz_name=resolved_biz_name or "",
        niche=resolved_niche or "",
        analysis_id=analysis_id
    )

@router.get("/geo-benchmark", response_model=GeoBenchmarkReport)
async def run_live_geo_benchmark(
    domain: Optional[str] = None,
    biz_name: Optional[str] = None,
    industry: Optional[str] = None,
    locale: str = "en-US",
    mode: str = "concise",
    analysis_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Live AI Retrieval Benchmark (Layer 2).
    Executes standardized multi-category benchmark suites across active AI engines
    (ChatGPT, Perplexity, Gemini, Claude, Groq). Stores immutable raw responses.
    """
    resolved_domain = domain
    resolved_biz_name = biz_name
    resolved_industry = industry

    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report and run.report.business_profile:
            bp = run.report.business_profile
            resolved_domain = resolved_domain or bp.primary_domain or run.website_url
            resolved_biz_name = resolved_biz_name or bp.business_name
            resolved_industry = resolved_industry or bp.industry

    if not resolved_domain and not resolved_biz_name:
        raise HTTPException(status_code=400, detail="Target domain or business name is required for GEO benchmark.")

    benchmark_mode = "comprehensive" if mode.lower() == "comprehensive" else "concise"
    return await benchmark_runner.execute_benchmark(
        domain=resolved_domain or "",
        brand_name=resolved_biz_name,
        industry=resolved_industry,
        locale=locale,
        mode=benchmark_mode,
    )

@router.get("/lead-gen", response_model=list[CommercialOpportunity])
async def get_commercial_opportunities(
    domain: Optional[str] = None,
    biz_name: Optional[str] = None,
    niche: Optional[str] = None,
    analysis_id: Optional[str] = None,
    user: Optional[UserIdentity] = Depends(get_current_user_optional),
):
    """
    Commercial Lead-Generation Void Detector & 1-Click Landing Page Generator.
    Identifies lucrative buyer queries that competitors cite, generating instant landing page blueprints.
    """
    resolved_domain = domain
    resolved_biz_name = biz_name
    resolved_niche = niche

    if analysis_id:
        run = _owned_analysis(analysis_id, user)
        if run and run.report and run.report.business_profile:
            bp = run.report.business_profile
            resolved_domain = resolved_domain or bp.primary_domain or run.website_url
            resolved_biz_name = resolved_biz_name or bp.business_name
            resolved_niche = resolved_niche or bp.industry

    if not resolved_domain and not resolved_biz_name:
        raise HTTPException(status_code=400, detail="Target domain or business name is required for commercial opportunity detection.")

    return lead_gen_engine.detect_commercial_opportunities(
        domain=resolved_domain or "",
        biz_name=resolved_biz_name or "",
        niche=resolved_niche or "",
        analysis_id=analysis_id
    )

@router.get("/agency", response_model=AgencyWorkspaceSummary)
async def get_agency_workspace(user: UserIdentity = Depends(get_current_user)):
    """
    Agency Mode Workspace: Manage Client A, B, C, D, E with white-label reports & client dashboards.
    """
    return agency_manager.get_workspace_summary(agency_id=user.org_id)

@router.post("/agency/clients", response_model=AgencyClientAccount)
async def add_agency_client(
    req: AddAgencyClientRequest,
    user: UserIdentity = Depends(get_current_user),
):
    """Add a new client domain to the Agency Workspace."""
    return agency_manager.add_client(client_name=req.client_name, domain=req.domain, org_id=user.org_id)

@router.delete("/agency/clients/{client_id}")
async def delete_agency_client(
    client_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Remove a managed client domain from the Agency Workspace."""
    success = agency_manager.remove_client(client_id, org_id=user.org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"deleted": True, "client_id": client_id}
