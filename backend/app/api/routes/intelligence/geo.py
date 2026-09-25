"""
Dristik AI GEO/AEO Live Pipeline API Routes
Endpoints to trigger live LLM querying, fetch historical time-series trends,
and inspect raw verbatim response texts with citation provenance.
"""
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

router = APIRouter(prefix="/geo-pipeline", tags=["GEO/AEO Pipeline"])


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
