"""Displayed score stays unmeasured when the report has no measured pillars."""
from app.scoring.score_explanations import displayed_composite, explain_displayed_score


def test_empty_report_has_no_displayed_composite():
    explained = explain_displayed_score({})
    assert displayed_composite({}) is None
    assert explained["composite"] is None
    assert explained["grade"] is None
    assert explained["live_execution_proven"] is False
