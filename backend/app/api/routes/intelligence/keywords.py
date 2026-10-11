"""
Keyword Intelligence & SERP Tracking API Endpoints
Manages continuous tracked keywords, daily SERP rank history, SERP features, and competitor ranks.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user

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


def _project(user: UserIdentity) -> str:
    return user.org_id


def _owned_keyword(user: UserIdentity, keyword_id: str):
    keywords = serp_tracking_engine.list_keywords(_project(user), active_only=False)
    match = next((item for item in keywords if item.keyword_id == keyword_id), None)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return match


@router.post("", response_model=TrackedKeyword, status_code=status.HTTP_201_CREATED)
def add_tracked_keyword(
    payload: TrackedKeywordCreate,
    user: UserIdentity = Depends(get_current_user),
) -> TrackedKeyword:
    """Add a new keyword to continuous daily SERP tracking for the signed-in organization."""
    try:
        return serp_tracking_engine.add_keyword(
            project_id=_project(user),
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
    project_id: str = Query("", description="Ignored. Keywords are scoped to the signed-in organization."),
    active_only: bool = Query(True, description="Filter only active keywords"),
    user: UserIdentity = Depends(get_current_user),
) -> List[TrackedKeyword]:
    """List tracked keywords for the signed-in organization."""
    del project_id
    return serp_tracking_engine.list_keywords(_project(user), active_only=active_only)


@router.delete("/{keyword_id}")
def remove_tracked_keyword(
    keyword_id: str,
    project_id: str = Query("", description="Ignored. Keywords are scoped to the signed-in organization."),
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a keyword from active tracking."""
    del project_id
    _owned_keyword(user, keyword_id)
    deleted = serp_tracking_engine.remove_keyword(_project(user), keyword_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return {"ok": True, "keyword_id": keyword_id}


@router.get("/{keyword_id}/history", response_model=List[KeywordSerpSnapshot])
def get_keyword_history(
    keyword_id: str,
    days: int = Query(30, ge=1, le=365, description="Number of historical days"),
    user: UserIdentity = Depends(get_current_user),
) -> List[KeywordSerpSnapshot]:
    """Retrieve daily SERP position timeline and feature snapshots for a keyword."""
    _owned_keyword(user, keyword_id)
    return serp_tracking_engine.get_history(keyword_id, days=days)


@router.get("/{keyword_id}/competitors")
def get_keyword_competitors(
    keyword_id: str,
    snapshot_date: Optional[str] = Query(None, description="Optional YYYY-MM-DD date"),
    user: UserIdentity = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieve competitor rank positions for this keyword on the SERP."""
    _owned_keyword(user, keyword_id)
    return serp_tracking_engine.get_competitor_ranks(keyword_id, snapshot_date=snapshot_date)


@router.post("/sync")
def sync_project_keywords(
    payload: SyncKeywordsRequest,
    user: UserIdentity = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger on-demand or daily SERP sync for all active keywords of a project.
    Captures live Google positions, AI Overviews, Snippets, and competitor ranks.
    """
    return serp_tracking_engine.sync_keyword_serp(
        project_id=_project(user),
        domain=payload.domain,
        competitor_domains=payload.competitor_domains,
    )


@router.get("/movement-summary", response_model=KeywordMovementSummary)
def get_keyword_movement_summary(
    project_id: str = Query("", description="Ignored. Keywords are scoped to the signed-in organization."),
    user: UserIdentity = Depends(get_current_user),
) -> KeywordMovementSummary:
    """Returns high-level movement metrics: Page 1 breakouts, Top 3 dominance, drops, and AI overview presence."""
    del project_id
    keywords = serp_tracking_engine.list_keywords(_project(user), active_only=True)
    return serp_tracking_engine.calculate_movement_summary(keywords)


class KeywordGapRequest(BaseModel):
    target_domain: str
    competitor_domains: List[str] = []
    project_id: Optional[str] = None


@router.post("/gap", response_model=KeywordGapReport)
def evaluate_keyword_gap(
    payload: KeywordGapRequest,
    user: UserIdentity = Depends(get_current_user),
) -> KeywordGapReport:
    """
    Evaluates competitor keyword gaps and computes traffic opportunity.
    Identifies missing top-10 keywords and weak page-2 keywords with recommended page creations.
    """
    from app.intelligence.competitive.keyword_gap import keyword_gap_engine
    return keyword_gap_engine.evaluate_gap(
        target_domain=payload.target_domain,
        competitor_domains=payload.competitor_domains,
        project_id=_project(user),
    )

