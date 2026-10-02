"""
Keyword Intelligence & SERP Tracking API Endpoints
Manages continuous tracked keywords, daily SERP rank history, SERP features, and competitor ranks.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.domain.models import (
    KeywordGapReport,
    KeywordMovementSummary,
    KeywordSerpSnapshot,
    TrackedKeyword,
    TrackedKeywordCreate,
)
from app.intelligence.serp_tracker import serp_tracking_engine

router = APIRouter(prefix="/intelligence/keywords", tags=["Keyword Intelligence & SERP Tracking"])


class SyncKeywordsRequest(BaseModel):
    project_id: str
    domain: str
    competitor_domains: List[str] = []


@router.post("", response_model=TrackedKeyword, status_code=status.HTTP_201_CREATED)
def add_tracked_keyword(payload: TrackedKeywordCreate) -> TrackedKeyword:
    """Add a new keyword to continuous daily SERP tracking."""
    try:
        return serp_tracking_engine.add_keyword(
            project_id=payload.project_id,
            domain=payload.domain,
            keyword=payload.keyword,
            target_url=payload.target_url,
            intent=payload.intent or "Commercial",
            tags=payload.tags,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to add keyword: {str(exc)}",
        )


@router.get("", response_model=List[TrackedKeyword])
def list_tracked_keywords(
    project_id: str = Query(..., description="Project ID"),
    active_only: bool = Query(True, description="Filter only active keywords"),
) -> List[TrackedKeyword]:
    """List all continuous tracked keywords for a project with current rank and 24h delta."""
    return serp_tracking_engine.list_keywords(project_id, active_only=active_only)


@router.delete("/{keyword_id}")
def remove_tracked_keyword(
    keyword_id: str,
    project_id: str = Query(..., description="Project ID"),
) -> Dict[str, Any]:
    """Remove a keyword from active tracking."""
    deleted = serp_tracking_engine.remove_keyword(project_id, keyword_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return {"ok": True, "keyword_id": keyword_id}


@router.get("/{keyword_id}/history", response_model=List[KeywordSerpSnapshot])
def get_keyword_history(
    keyword_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of historical days"),
) -> List[KeywordSerpSnapshot]:
    """Retrieve daily SERP position timeline and feature snapshots for a keyword."""
    return serp_tracking_engine.get_history(keyword_id, days=days)


@router.get("/{keyword_id}/competitors")
def get_keyword_competitors(
    keyword_id: str,
    snapshot_date: Optional[str] = Query(None, description="Optional YYYY-MM-DD date"),
) -> List[Dict[str, Any]]:
    """Retrieve competitor rank positions for this keyword on the SERP."""
    return serp_tracking_engine.get_competitor_ranks(keyword_id, snapshot_date=snapshot_date)


@router.post("/sync")
def sync_project_keywords(payload: SyncKeywordsRequest) -> Dict[str, Any]:
    """
    Trigger on-demand or daily SERP sync for all active keywords of a project.
    Captures live Google positions, AI Overviews, Snippets, and competitor ranks.
    """
    return serp_tracking_engine.sync_keyword_serp(
        project_id=payload.project_id,
        domain=payload.domain,
        competitor_domains=payload.competitor_domains,
    )


@router.get("/movement-summary", response_model=KeywordMovementSummary)
def get_keyword_movement_summary(
    project_id: str = Query(..., description="Project ID"),
) -> KeywordMovementSummary:
    """Returns high-level movement metrics: Page 1 breakouts, Top 3 dominance, drops, and AI overview presence."""
    keywords = serp_tracking_engine.list_keywords(project_id, active_only=True)
    return serp_tracking_engine.calculate_movement_summary(keywords)


class KeywordGapRequest(BaseModel):
    target_domain: str
    competitor_domains: List[str] = []
    project_id: Optional[str] = None


@router.post("/gap", response_model=KeywordGapReport)
def evaluate_keyword_gap(payload: KeywordGapRequest) -> KeywordGapReport:
    """
    Evaluates competitor keyword gaps and computes traffic opportunity.
    Identifies missing top-10 keywords and weak page-2 keywords with recommended page creations.
    """
    from app.intelligence.competitive.keyword_gap import keyword_gap_engine
    return keyword_gap_engine.evaluate_gap(
        target_domain=payload.target_domain,
        competitor_domains=payload.competitor_domains,
        project_id=payload.project_id,
    )

