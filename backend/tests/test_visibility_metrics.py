from app.geo.visibility_metrics import compute_visibility_metrics


def test_failed_runs_stay_out_of_the_denominator():
    metrics = compute_visibility_metrics([
        {"status": "SUCCESS", "brand_mentioned": True, "brand_cited": True, "commercial_intent": "comparison", "position_prominence": "PRIMARY_RECOMMENDATION", "competitors_cited": [{"name": "Rival"}]},
        {"status": "SUCCESS", "brand_mentioned": False, "brand_cited": False, "commercial_intent": "informational"},
        {"status": "TIMEOUT", "brand_mentioned": False, "brand_cited": False},
        {"status": "BLOCKED", "brand_mentioned": False},
    ])
    assert metrics["valid_responses"] == 2
    assert metrics["failed_or_blocked"] == 2
    assert metrics["mentions"] == 1
    assert metrics["mention_rate_pct"] == 50.0
    assert metrics["citation_rate_pct"] == 50.0
    assert metrics["recommendation_responses"] == 1
    assert metrics["recommendations"] == 1
    assert metrics["recommendation_rate_pct"] == 100.0
    assert metrics["citation_share_pct"] == 50.0


def test_empty_executions_are_not_a_zero():
    metrics = compute_visibility_metrics([])
    assert metrics["valid_responses"] == 0
    assert metrics["mention_rate_pct"] is None
    assert metrics["recommendation_rate_pct"] is None
    assert metrics["citation_rate_pct"] is None
    assert metrics["citation_share_pct"] is None
