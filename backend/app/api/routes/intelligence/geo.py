"""
Dristik AI GEO/AEO Live Pipeline API Routes
Endpoints to trigger live LLM querying, fetch historical time-series trends,
and inspect raw verbatim response texts with citation provenance.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.intelligence.geo.pipeline_store import (
    geo_pipeline_store,
    GeoSnapshotSummary,
    GeoSnapshotDetail,
)
from app.intelligence.geo.pipeline_runner import (
    geo_pipeline_runner,
    FIXED_PROMPT_SET,
)
from app.intelligence.geo.citation_gap import (
    geo_citation_gap_engine,
    CausalCitationGapReport,
)
from app.intelligence.geo.benchmark_generator import (
    benchmark_generator,
    BenchmarkSuite,
)
from app.intelligence.geo.benchmark_runner import (
    benchmark_runner,
    ShareOfModelMetric,
    EvaluatedQueryRun,
)
from app.intelligence.geo.crawler_logs import (
    crawler_log_analyzer,
    CrawlerLogAnalysis,
)
from app.intelligence.geo.sentiment_engine import (
    geo_sentiment_engine,
    HallucinationAuditReport,
)
from app.intelligence.geo.semantic_retrieval import (
    semantic_retrieval_analyzer,
    rag_retrieval_simulator,
    ControlledRetrievalReport,
    RagSimulationReport,
    RetrievalAnalysisConfig,
)
from app.intelligence.geo.offpage_network import (
    offpage_network_analyzer,
    OffPageCitationReport,
)
from app.intelligence.geo.displacement_sentinel import (
    displacement_sentinel,
    DisplacementAnalysisResult,
)
from app.intelligence.geo.attribution_engine import (
    geo_attribution_engine,
    GeoAttributionReport,
)
from app.intelligence.geo.remediation_classifier import (
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


