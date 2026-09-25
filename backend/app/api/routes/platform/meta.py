"""
Meta & Rubric API Routes
Provides public inspection of scoring methodologies, policy versions, and platform definitions.
"""
from fastapi import APIRouter
from app.scoring.scoring_rubric import get_scoring_rubric_v4

router = APIRouter(prefix="/meta", tags=["Platform Meta & Governance"])


@router.get("/scoring-rubric")
def get_scoring_rubric():
    """Returns the published mathematical rubric, component weights, and confidence gating rules."""
    return get_scoring_rubric_v4()
