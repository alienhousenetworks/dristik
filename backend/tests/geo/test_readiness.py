"""On-page GEO readiness does not count as a live citation measurement."""
from app.intelligence.geo.readiness import evaluate_geo_readiness


def test_readiness_without_a_live_run_is_not_measured():
    report = evaluate_geo_readiness(website_url="https://example.com", pages=[])
    assert report.visibility_status == "NOT_CONFIGURED"
    visibility = report.dimension_scores["ai_engine_visibility"]
    assert visibility.is_measured is False
