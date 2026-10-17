"""Displayed-score explanation.

The composite is calculated by displayed_score.displayed_composite. This module
does not apply a second formula.
"""
from app.persistence.models import ScoreExplanation, ScoreExplanationDimension
from app.domain.scoring.displayed_score import (
    align_story_score,
    displayed_composite,
    first_story_score,
    grade_for_displayed,
    live_execution_proven,
)

__all__ = [
    "ScoreExplanation",
    "ScoreExplanationDimension",
    "align_story_score",
    "displayed_composite",
    "explain_displayed_score",
    "first_story_score",
    "grade_for_displayed",
    "live_execution_proven",
]


def explain_displayed_score(report) -> dict:
    composite = displayed_composite(report)
    return {
        "composite": composite,
        "grade": grade_for_displayed(composite) if composite is not None else None,
        "live_execution_proven": live_execution_proven(report),
    }
