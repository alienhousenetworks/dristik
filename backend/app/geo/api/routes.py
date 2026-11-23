"""
Dristik AI GEO/AEO Live Pipeline API Routes
Endpoints to trigger live LLM querying, fetch historical time-series trends,
and inspect raw verbatim response texts with citation provenance.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.geo.pipeline_store import (
    geo_pipeline_store,
    GeoSnapshotSummary,
    GeoSnapshotDetail,
)
from app.geo.pipeline_runner import (
    geo_pipeline_runner,
    FIXED_PROMPT_SET,
)
from app.geo.citation_gap import (
    geo_citation_gap_engine,
    CausalCitationGapReport,
)
from app.geo.benchmark_generator import (
    benchmark_generator,
    BenchmarkSuite,
)
from app.geo.benchmark_runner import (
    benchmark_runner,
    ShareOfModelMetric,
    EvaluatedQueryRun,
)
from app.geo.crawler_logs import (
    crawler_log_analyzer,
    CrawlerLogAnalysis,
)
from app.geo.sentiment_engine import (
    geo_sentiment_engine,
    HallucinationAuditReport,
)
from app.geo.semantic_retrieval import (
    semantic_retrieval_analyzer,
    rag_retrieval_simulator,
    ControlledRetrievalReport,
    RagSimulationReport,
    RetrievalAnalysisConfig,
)
from app.geo.offpage_network import (
    offpage_network_analyzer,
    OffPageCitationReport,
)
from app.geo.displacement_sentinel import (
    displacement_sentinel,
    DisplacementAnalysisResult,
)
from app.geo.attribution_engine import (
    geo_attribution_engine,
    GeoAttributionReport,
)
from app.geo.remediation_classifier import (
    build_evidence_grounded_aeo_remediations,
    AeoRemediationPack,
)

router = APIRouter(prefix="/geo-pipeline", tags=["GEO/AEO Pipeline"])


class CitationGapAnalysisRequest(BaseModel):
    domain: str = Field(..., description="Target website domain (e.g. acme.com)")
    brand_name: Optional[str] = Field(None, description="Organization brand name")
    competitors: List[str] = Field(default_factory=list, description="Competitor domains to evaluate against")


class RunGeoPipelineRequest(BaseModel):
    domain: str = Field(..., description="Website domain or URL to evaluate (e.g. alienhousenetworks.com)")
    brand_name: Optional[str] = Field(None, description="Organization or brand name")
    industry: Optional[str] = Field(None, description="Industry category or niche")


class GeoTrendResponse(BaseModel):
    domain: str
    current_score: Optional[int] = None
    latest_delta: Optional[int] = None
    total_snapshots: int = 0
    history: List[GeoSnapshotSummary] = Field(default_factory=list)
    engine_trends: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    first_tracked: Optional[str] = None
    last_tracked: Optional[str] = None
    canonical_prompts: List[Dict[str, str]] = Field(default_factory=list)


@router.post("/run", response_model=GeoSnapshotDetail)
async def run_geo_pipeline_snapshot(req: RunGeoPipelineRequest):
    """
    Fires the fixed 6-prompt canonical query set at live LLM answer engines
    (OpenAI, Anthropic, Perplexity, Gemini), parses raw outputs, computes
    deltas vs prior runs, and stores a new historical time-series snapshot.
    """
    try:
        snapshot = await geo_pipeline_runner.execute_live_pipeline(
            domain=req.domain,
            brand_name=req.brand_name,
            industry=req.industry,
        )
        return snapshot
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to execute live GEO pipeline: {str(exc)}")


@router.get("/trends", response_model=GeoTrendResponse)
async def get_geo_pipeline_trends(
    domain: str = Query(..., description="Target domain to inspect"),
    limit: int = Query(30, ge=1, le=100, description="Max history points to return")
):
    """
    Returns the time-series citation history and delta trend for a domain,
    enabling multi-point historical trajectory inspection across AI engines.
    """
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").split("/")[0]
    history = geo_pipeline_store.get_domain_history(clean_domain, limit=limit)

    if not history:
        return GeoTrendResponse(
            domain=clean_domain,
            current_score=None,
            latest_delta=None,
            total_snapshots=0,
            history=[],
            engine_trends={},
            canonical_prompts=FIXED_PROMPT_SET
        )

    latest = history[-1]
    earliest = history[0]

    # Assemble per-engine time series
    engine_series: Dict[str, List[Dict[str, Any]]] = {}
    for snap in history:
        for eng_name, score in snap.engine_scores.items():
            if eng_name not in engine_series:
                engine_series[eng_name] = []
            engine_series[eng_name].append({
                "timestamp": snap.timestamp,
                "score": score
            })

    return GeoTrendResponse(
        domain=clean_domain,
        current_score=latest.overall_score,
        latest_delta=latest.delta_score,
        total_snapshots=len(history),
        history=history,
        engine_trends=engine_series,
        first_tracked=earliest.timestamp,
        last_tracked=latest.timestamp,
        canonical_prompts=FIXED_PROMPT_SET
    )


@router.get("/snapshots/{snapshot_id}", response_model=GeoSnapshotDetail)
async def get_geo_snapshot_detail(snapshot_id: str):
    """
    Returns full raw verbatim model responses, citation URLs, and query records
    for a specific historical snapshot (Zero-Fake audit inspection).
    """
    detail = geo_pipeline_store.get_snapshot_detail(snapshot_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"GEO snapshot '{snapshot_id}' not found.")
    return detail


@router.get("/tracked-domains")
async def list_geo_tracked_domains():
    """
    Lists all domains actively monitored by the GEO/AEO pipeline with snapshot counts.
    """
    domains = geo_pipeline_store.list_tracked_domains()
    return {"domains": domains, "total_count": len(domains)}


@router.post("/citation-gap", response_model=CausalCitationGapReport)
async def analyze_citation_gaps_endpoint(req: CitationGapAnalysisRequest):
    """
    Executes Causal Citation Gap Analysis (Layers 3 & 4 of GEO architecture).
    Reverse-engineers why competitors win AI citations and emits exact drop-in
    copy, schema, and llms.txt patches.
    """
    try:
        report = geo_citation_gap_engine.analyze_citation_gaps(
            target_domain=req.domain,
            brand_name=req.brand_name,
            competitor_domains=req.competitors,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyze citation gaps: {str(exc)}")


class DynamicFanOutClusterRequest(BaseModel):
    domain: str = Field(..., description="Target domain (e.g. acme.com)")
    brand_name: Optional[str] = Field(None, description="Brand name")
    industry: Optional[str] = Field(None, description="Industry or category label")
    competitors: List[str] = Field(default_factory=list, description="Competitor names or domains")
    personas: Optional[List[str]] = Field(None, description="Buyer personas to cluster (e.g. Enterprise Architect, CFO)")
    target_size: int = Field(50, ge=10, le=200, description="Target query suite size")


class ShareOfModelRequest(BaseModel):
    domain: str = Field(..., description="Target domain")
    brand_name: Optional[str] = Field(None, description="Brand name")
    competitors: List[str] = Field(default_factory=list, description="Competitors to evaluate displacement against")
    evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Evaluated query runs to score")


class CrawlerLogAnalysisRequest(BaseModel):
    log_content: str = Field(..., description="Raw server/CDN access log text (Nginx/Cloudflare)")


@router.post("/fanout-cluster", response_model=BenchmarkSuite)
async def generate_fanout_cluster_endpoint(req: DynamicFanOutClusterRequest):
    """
    Generates a dynamic multi-persona intent cluster of benchmark queries
    accompanied by reverse-engineered AI search fan-out sub-queries.
    """
    try:
        suite = benchmark_generator.generate_dynamic_cluster(
            domain=req.domain,
            brand_name=req.brand_name,
            industry=req.industry,
            competitors=req.competitors,
            personas=req.personas,
            target_size=req.target_size,
        )
        return suite
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate fan-out cluster: {str(exc)}")


@router.post("/share-of-model", response_model=ShareOfModelMetric)
async def calculate_share_of_model_endpoint(req: ShareOfModelRequest):
    """
    Computes enterprise Share of Model (SoM), ordinal position distributions,
    and competitor displacement instances where rivals captured top AI recommendations.
    """
    try:
        metric = benchmark_runner.calculate_share_of_model(
            evaluations=req.evaluations,
            target_domain=req.domain,
            brand_name=req.brand_name or req.domain.split(".")[0].capitalize(),
            competitors=req.competitors,
        )
        return metric
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to calculate Share of Model: {str(exc)}")


@router.post("/crawler-logs/analyze", response_model=CrawlerLogAnalysis)
async def analyze_crawler_logs_endpoint(req: CrawlerLogAnalysisRequest):
    """
    Analyzes server or CDN access logs (Cloudflare, Nginx, Apache) to measure
    real AI search crawler activity (GPTBot, PerplexityBot, ClaudeBot), blocked hits, and crawl health.
    """
    try:
        analysis = crawler_log_analyzer.analyze_logs(req.log_content)
        return analysis
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyze crawler logs: {str(exc)}")


class ControlledRetrievalRequest(BaseModel):
    page_text: Optional[str] = Field(None, description="Crawled web page body text to chunk and evaluate")
    query: str = Field(..., description="Target buyer query to test semantic retrieval alignment against")
    source_url: Optional[str] = Field("https://target.domain/", description="Source URL of page")
    chunk_size: int = Field(250, ge=50, le=800, description="Dristik chunk word count")
    chunk_overlap: int = Field(40, ge=0, le=200, description="Dristik chunk overlap words")
    similarity_threshold: float = Field(0.72, ge=0.0, le=1.0, description="Dristik retrieval qualification threshold")
    top_k: int = Field(3, ge=1, le=20, description="Number of top qualifying chunks to retrieve")


# Backward-compatible alias
SimulateRagRequest = ControlledRetrievalRequest


@router.post("/controlled-retrieval", response_model=ControlledRetrievalReport)
async def controlled_retrieval_endpoint(req: ControlledRetrievalRequest):
    """
    Executes Dristik's controlled semantic retrieval analysis over crawled website content.
    Applies deterministic sentence-window chunking, configured embeddings (intfloat/e5-small-v2),
    and cosine similarity against the target query.

    NOTE: This is Dristik's controlled retrieval methodology; it does not measure or simulate
    proprietary internal retrieval architectures of external AI engines.
    """
    try:
        cfg = RetrievalAnalysisConfig(
            chunk_size=req.chunk_size,
            chunk_overlap=req.chunk_overlap,
            similarity_threshold=req.similarity_threshold,
            top_k=req.top_k,
        )
        report = semantic_retrieval_analyzer.analyze_page_content(
            page_text=req.page_text,
            query=req.query,
            source_url=req.source_url or "https://target.domain/",
            config=cfg,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to execute controlled retrieval analysis: {str(exc)}")


@router.post("/simulate-rag", response_model=ControlledRetrievalReport, deprecated=True)
async def simulate_rag_endpoint(req: ControlledRetrievalRequest):
    """
    Deprecated alias for /controlled-retrieval.
    """
    return await controlled_retrieval_endpoint(req)


class SentimentAuditRequest(BaseModel):
    evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Evaluated query runs to audit")
    brand_name: str = Field(..., description="Brand name to evaluate sentiment and hallucinations for")


class OffPageNetworkRequest(BaseModel):
    evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Evaluated query runs to analyze")
    domain: str = Field(..., description="Target website domain")
    brand_name: str = Field(..., description="Target brand name")
    competitors: Optional[List[str]] = Field(default_factory=list, description="Competitor domains or brand names")


class DisplacementDetectionRequest(BaseModel):
    baseline_evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Baseline evaluated query runs")
    current_evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Current evaluated query runs")
    brand_name: str = Field(..., description="Target brand name")
    domain: str = Field(..., description="Target domain")
    competitors: Optional[List[str]] = Field(default_factory=list, description="Competitor brand names or domains")


class AttributionVerificationRequest(BaseModel):
    pre_patch_evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Pre-patch evaluated query runs")
    post_patch_evaluations: List[EvaluatedQueryRun] = Field(default_factory=list, description="Post-patch evaluated query runs")
    domain: str = Field(..., description="Target domain")
    brand_name: str = Field(..., description="Target brand name")
    pre_run_id: str = Field("pre_patch", description="Pre-patch run identifier")
    post_run_id: str = Field("post_patch", description="Post-patch run identifier")


@router.post("/sentiment-audit", response_model=HallucinationAuditReport)
async def audit_sentiment_endpoint(req: SentimentAuditRequest):
    """
    Audits verbatim AI answer engine responses for brand sentiment polarity,
    associated brand traits, and ground-truth factual hallucinations.
    """
    try:
        report = geo_sentiment_engine.generate_audit_report(
            evaluations=req.evaluations,
            brand_name=req.brand_name,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to audit sentiment and hallucinations: {str(exc)}")


@router.post("/offpage-network", response_model=OffPageCitationReport)
async def analyze_offpage_network_endpoint(req: OffPageNetworkRequest):
    """
    Audits third-party authority hubs (Reddit, G2, TechCrunch, Wikipedia)
    feeding generative search answers and generates a targeted profile acquisition roadmap.
    """
    try:
        report = offpage_network_analyzer.analyze_citation_network(
            evaluations=req.evaluations,
            target_domain=req.domain,
            brand_name=req.brand_name,
            competitors=req.competitors,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to analyze off-page citation network: {str(exc)}")


@router.post("/detect-displacements", response_model=DisplacementAnalysisResult)
async def detect_displacements_endpoint(req: DisplacementDetectionRequest):
    """
    Compares two benchmark evaluation sets to isolate competitor conquesting,
    position drops, and lost citations across live AI engines.
    """
    try:
        result = displacement_sentinel.detect_displacements(
            baseline_evaluations=req.baseline_evaluations,
            current_evaluations=req.current_evaluations,
            target_brand=req.brand_name,
            target_domain=req.domain,
            competitors=req.competitors,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to detect displacements: {str(exc)}")


@router.post("/verify-attribution", response_model=GeoAttributionReport)
async def verify_attribution_endpoint(req: AttributionVerificationRequest):
    """
    Measures causal before/after deltas following remediation patch deployments,
    quantifying mention rate gains, citation gains, and Share of Model ROI.
    """
    try:
        report = geo_attribution_engine.calculate_attribution(
            pre_patch_evaluations=req.pre_patch_evaluations,
            post_patch_evaluations=req.post_patch_evaluations,
            target_domain=req.domain,
            brand_name=req.brand_name,
            pre_run_id=req.pre_run_id,
            post_run_id=req.post_run_id,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to verify attribution deltas: {str(exc)}")


class AeoRemediationRequest(BaseModel):
    domain: str
    brand_name: Optional[str] = None
    website_url: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None


@router.post("/remediation-pack", response_model=AeoRemediationPack)
async def generate_remediation_pack_endpoint(req: AeoRemediationRequest):
    """
    Synthesizes evidence-grounded AEO remediation patches:
    1. Verified 40-60 word definition answer blocks.
    2. Validated Schema.org FAQPage JSON-LD snippet (only for verified questions).
    3. CONTENT_REQUIRED advisories for unstated business policies.
    """
    try:
        from app.domain.models import GeoQuestionEvidence
        raw_qs = req.questions or []
        qs = [GeoQuestionEvidence(**q) for q in raw_qs] if raw_qs else []
        url = req.website_url or f"https://{req.domain}"
        brand = req.brand_name or req.domain.split(".")[0].capitalize()

        return build_evidence_grounded_aeo_remediations(
            questions=qs,
            brand_name=brand,
            website_url=url,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to synthesize AEO remediation pack: {str(exc)}")


# ============================================================================
# GeoLook-Integrated Endpoints (Phases 1–5): Access Diagnostics, Draft Linter,
# Search Demand Mining, Manual Sampling & Declarative Verification
# ============================================================================

class AccessDiagnosticsRequest(BaseModel):
    website_url: str
    robots_txt: str = ""
    pages: List[Dict[str, Any]] = Field(default_factory=list)
    has_sitemap: bool = False
    sitemap_urls: List[str] = Field(default_factory=list)
    has_llms_txt: bool = False
    run_live_ua_probe: bool = False
    run_live_llms_check: bool = False
    quotability_score: Optional[float] = None


@router.post("/access-diagnostics")
async def access_diagnostics_endpoint(req: AccessDiagnosticsRequest):
    """Run RFC 9309 robots, optional active WAF AI-UA probing, llms.txt validation, and 4-layer dependency chain."""
    from app.geo.agent_readiness import validate_llms_txt
    from app.geo.dependency_chain import evaluate_dependency_chain
    from app.geo.intelligence.crawler_accessibility import CrawlerAccessibilityEngine

    ua_probe_res: Dict[str, Any] = {"ai_ua_probe": {}, "ai_ua_blocked": []}
    if req.run_live_ua_probe:
        ua_probe_res = await CrawlerAccessibilityEngine.probe_ai_user_agents(
            root_url=req.website_url, robots_txt=req.robots_txt
        )

    llms_check: Optional[Dict[str, Any]] = None
    has_llms = req.has_llms_txt
    if req.run_live_llms_check:
        llms_check = await validate_llms_txt(req.website_url, robots_txt=req.robots_txt)
        has_llms = bool(llms_check.get("present"))

    crawler_report = CrawlerAccessibilityEngine.evaluate_crawler_access(
        robots_txt=req.robots_txt,
        ai_ua_probe=ua_probe_res.get("ai_ua_probe"),
    )
    chain = evaluate_dependency_chain(
        pages=req.pages,
        robots_txt=req.robots_txt,
        has_sitemap=req.has_sitemap,
        sitemap_urls=req.sitemap_urls,
        has_llms_txt=has_llms,
        llms_txt_check=llms_check,
        ai_ua_blocked=ua_probe_res.get("ai_ua_blocked") or [],
        quotability_score=req.quotability_score,
    )
    return {
        "crawler_accessibility": crawler_report.model_dump(),
        "llms_txt_validation": llms_check,
        "dependency_chain": chain.model_dump(),
    }


class DraftLintRequest(BaseModel):
    text: str
    verified_numbers: List[str] = Field(default_factory=list)
    verified_facts_text: str = ""
    unconfirmed_competitors: List[str] = Field(default_factory=list)


@router.post("/draft-lint")
async def draft_lint_endpoint(req: DraftLintRequest):
    """Run fabrication-risk linting on any GEO/AEO content draft before approval or publishing."""
    from app.geo.draft_linter import lint_draft

    return lint_draft(
        req.text,
        verified_numbers=req.verified_numbers,
        verified_facts_text=req.verified_facts_text,
        unconfirmed_competitors=req.unconfirmed_competitors,
    ).model_dump()


class DemandMineRequest(BaseModel):
    brand_name: str
    category: str = ""
    competitors: List[str] = Field(default_factory=list)
    market: str = "global"
    previous_first_seen: Dict[str, str] = Field(default_factory=dict)


@router.post("/demand-mine")
async def demand_mine_endpoint(req: DemandMineRequest):
    """Mine real buyer-intent search autocomplete suggestions with rising-demand snapshot diffing."""
    from app.geo.demand_miner import mine_search_demand

    snap = await mine_search_demand(
        brand_name=req.brand_name,
        category=req.category,
        competitors=req.competitors,
        market=req.market,
        previous_first_seen=req.previous_first_seen,
    )
    return snap.model_dump()


class ManualSheetImportRequest(BaseModel):
    tenant_id: str = "default"
    brand_name: str
    brand_aliases: List[str] = Field(default_factory=list)
    competitors: Dict[str, List[str]] = Field(default_factory=dict)
    own_domain: str = ""
    session_mode: str = "incognito"
    market: str = "global"
    sheet_markdown: str


@router.post("/manual-samples/import")
async def manual_samples_import_endpoint(req: ManualSheetImportRequest):
    """Import manual/browser AI answer sheet, compute visibility metrics, and extract competitor source gaps."""
    from app.geo.offpage_network import compute_competitor_source_gap
    from app.geo.sampling_manual import aggregate_manual_samples, import_sampling_sheet

    samples = import_sampling_sheet(
        req.sheet_markdown,
        tenant_id=req.tenant_id,
        brand_name=req.brand_name,
        brand_aliases=req.brand_aliases,
        competitors=req.competitors,
        own_domain=req.own_domain,
        session_mode=req.session_mode,
        market=req.market,
    )
    return {
        "imported_count": len(samples),
        "samples": [s.model_dump() for s in samples],
        "metrics": aggregate_manual_samples(samples),
        "source_gap": compute_competitor_source_gap(
            samples, brand_name=req.brand_name, own_host=req.own_domain
        ),
    }


class DeclarativeCheckRequest(BaseModel):
    check_expr: str
    audit_context: Dict[str, Any]
    metrics_context: Optional[Dict[str, Any]] = None
    baseline_value: Optional[Any] = None
    previous_passed: bool = False
    audited_at: Optional[str] = None
    verified_at: Optional[str] = None


@router.post("/verification/declarative-check")
async def declarative_check_endpoint(req: DeclarativeCheckRequest):
    """Run a declarative verification checker and freshness guard check."""
    from app.geo.reporting.freshness_guard import check_delivery_freshness
    from app.geo.verification_engine import run_declarative_check

    check_res = run_declarative_check(
        req.check_expr,
        audit_context=req.audit_context,
        metrics_context=req.metrics_context,
        baseline_value=req.baseline_value,
        previous_passed=req.previous_passed,
    )
    freshness = (
        check_delivery_freshness(audited_at=req.audited_at, verified_at=req.verified_at).model_dump()
        if req.audited_at
        else None
    )
    return {"check": check_res.model_dump(), "freshness": freshness}


# ── Phase 2: SRO (Selection Rate Optimization) ──────────────────────────────

class SROAnalyzeRequest(BaseModel):
    target_url: str = Field(..., min_length=4, max_length=2000)
    keyword: str = Field(..., min_length=1, max_length=250)
    country: str = Field(default="US", min_length=2, max_length=2)
    brand_name: Optional[str] = Field(default=None, max_length=120)
    competitor_urls: List[str] = Field(default_factory=list, max_length=5)
    engines: Optional[List[str]] = None
    use_llm_synthesis: bool = Field(default=False)
    synthesis_model: Optional[str] = Field(default=None, max_length=120)


class BulkSROItem(BaseModel):
    url: str = Field(..., min_length=4, max_length=2000)
    keyword: str = Field(..., min_length=1, max_length=250)


class BulkSRORequest(BaseModel):
    items: List[BulkSROItem] = Field(..., min_length=1, max_length=5)
    country: str = Field(default="US", min_length=2, max_length=2)


@router.post("/sro/analyze")
async def analyze_sro_endpoint(req: SROAnalyzeRequest):
    """Run provider-independent Selection Rate Optimization across configured AI providers."""
    from app.geo.sro import sro_engine

    res = await sro_engine.analyze(
        target_url=req.target_url,
        keyword=req.keyword,
        country=req.country.upper(),
        brand_name=req.brand_name,
        competitor_urls=req.competitor_urls,
        engines=req.engines,
        use_llm_synthesis=req.use_llm_synthesis,
        synthesis_model=req.synthesis_model,
    )
    return res.model_dump(mode="json")


@router.post("/sro/bulk")
async def bulk_sro_endpoint(req: BulkSRORequest):
    """SSE-streamed bulk SRO analysis across up to 5 (url, keyword) pairs."""
    import json
    from fastapi.responses import StreamingResponse
    from app.geo.sro import sro_engine

    async def _gen():
        yield f"event: start\ndata: {json.dumps({'total': len(req.items)})}\n\n"
        for idx, item in enumerate(req.items):
            yield f"event: progress\ndata: {json.dumps({'index': idx, 'url': item.url, 'keyword': item.keyword, 'stage': 'analyzing'})}\n\n"
            res = await sro_engine.analyze(
                target_url=item.url,
                keyword=item.keyword,
                country=req.country.upper(),
            )
            yield f"event: result\ndata: {json.dumps({'index': idx, 'result': res.model_dump(mode='json')})}\n\n"
        yield f"event: complete\ndata: {json.dumps({'total': len(req.items)})}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


# ── Phase 3: Rank Signal (Controlled A/B Passage Experiments) ───────────────

class RankSignalRunRequest(BaseModel):
    signal_id: str = Field(..., min_length=2, max_length=8)
    keyword: str = Field(..., min_length=1, max_length=250)
    target_url: str = Field(..., min_length=4, max_length=2000)
    passages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of {origin, url, text} passages (or omit to fetch target_url)",
    )
    judge_model: str = Field(default="gemini-2.0-flash")
    rewrite_model: str = Field(default="gemini-2.0-flash")
    max_trials: int = Field(default=40, ge=20, le=40)
    is_byok: bool = Field(default=False)
    byok_max_usd: Optional[float] = Field(default=None, ge=0.05, le=5.0)


@router.get("/rank-signal/catalog")
async def rank_signal_catalog_endpoint():
    """Return frozen 15-signal Rank Signal catalog (S00-S14) with credit pricing."""
    from app.geo.rank_signal import (
        BYOK_DEFAULT_MAX_USD,
        CATALOG_VERSION,
        CREDIT_COST_FULL_SUITE,
        FEATURE_CATALOG,
        RUN_ORDER,
        credit_cost_for_signal,
    )

    return {
        "catalog_version": CATALOG_VERSION,
        "run_order": RUN_ORDER,
        "full_suite_credits": CREDIT_COST_FULL_SUITE,
        "byok_default_max_usd": BYOK_DEFAULT_MAX_USD,
        "signals": [
            {
                "id": s.id,
                "name": s.name,
                "build": s.build,
                "expected": s.expected,
                "feature": s.feature,
                "credits": credit_cost_for_signal(s),
                "note": s.note,
            }
            for s in FEATURE_CATALOG
        ],
    }


@router.post("/rank-signal/run")
async def rank_signal_run_endpoint(req: RankSignalRunRequest):
    """SSE-streamed controlled A/B Rank Signal trial runner with credit accounting."""
    import json
    from fastapi.responses import StreamingResponse
    from app.geo.rank_signal import extract_passages, rank_signal_runner
    from app.geo.sro import fetch_page_snapshot

    raw_texts = [
        (p.get("origin") or "target", p.get("url") or req.target_url, p.get("text") or "")
        for p in req.passages
        if (p.get("text") or "").strip()
    ]
    if not raw_texts:
        snap = await fetch_page_snapshot(req.target_url)
        if snap.content_preview:
            raw_texts.append(("target", req.target_url, snap.content_preview))

    passages = extract_passages(raw_texts, keyword=req.keyword)

    async def _gen():
        async for ev_type, payload in rank_signal_runner.run_stream(
            signal_id=req.signal_id,
            keyword=req.keyword,
            target_url=req.target_url,
            passages=passages,
            judge_model=req.judge_model,
            rewrite_model=req.rewrite_model,
            max_trials=req.max_trials,
            is_byok=req.is_byok,
            byok_max_usd=req.byok_max_usd,
        ):
            yield f"event: {ev_type}\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


# ── Phase 5: Competitor Battlecards & Interactive Persona Fan-Out ───────────

class BattlecardsRequest(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=120)
    competitors: List[str] = Field(..., min_length=1, max_length=20)
    responses: List[Dict[str, Any]] = Field(default_factory=list)


class PersonaFanoutRequest(BaseModel):
    core_prompt: str = Field(..., min_length=3, max_length=500)
    personas: List[str] = Field(..., min_length=1, max_length=12)
    brand_name: str = Field(default="")


@router.post("/battlecards")
async def generate_battlecards_endpoint(req: BattlecardsRequest):
    """Synthesize competitor battlecards strictly from observed AI responses."""
    from app.geo.battlecards import CompetitorBattlecardGenerator

    rep = CompetitorBattlecardGenerator.generate(
        brand_name=req.brand_name,
        competitors=req.competitors,
        responses=req.responses,
    )
    return rep.model_dump(mode="json")


@router.post("/persona-fanout")
async def generate_persona_fanout_endpoint(req: PersonaFanoutRequest):
    """Generate persona-angled buyer prompt variants (zero LLM cost)."""
    from app.geo.battlecards import generate_persona_fanout_prompts

    variants = generate_persona_fanout_prompts(
        core_prompt=req.core_prompt,
        personas=req.personas,
        brand_name=req.brand_name,
    )
    return {"core_prompt": req.core_prompt, "count": len(variants), "variants": variants}




