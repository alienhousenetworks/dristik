"""Dossier score, SERP copy, and Google channel status stay internally consistent."""
from app.integrations.google_report import collect_google_performance, map_analytics, map_search_console
from app.remediation.serp_text import fit_serp_text
from app.scoring.displayed_score import align_story_score, displayed_composite, story_matches_composite


def _pillars(**extra):
    payload = {
        "scores": {"overall_score": 83, "grade": "B", "health_label": "Good"},
        "honest_scores": {
            "google_score": 79.6,
            "ai_readiness_score": 80,
            "human_score": 76.6,
            "live_ai_citation_score": 0,
            "ai_visibility_status": "MEASURED",
            "ai_visibility_score": 0,
        },
        "geo_readiness": {"extractability_score": 52.7},
    }
    payload.update(extra)
    return payload


def test_unproven_live_zero_is_excluded_from_the_composite():
    assert displayed_composite(_pillars()) == 69.8


def test_proven_live_zero_stays_in_the_composite():
    composite = displayed_composite(_pillars(ai_visibility_scorecard={
        "status": "MEASURED",
        "successful_runs": 4,
        "engines_measured": 1,
        "queries": 18,
        "citation_rate_pct": 0,
        "observatory_records": [{"engine_id": "claude", "brand_cited": False}],
    }))
    assert composite == 52.4


def test_story_sentence_uses_the_dossier_composite():
    story = "Acme scores 83/100 (B, Good). This figure is the weighted rollup of pillar scores."
    aligned = align_story_score(story, 83, 69.8)
    assert aligned.startswith("Acme scores 69.8/100 (grade C).")
    assert "83/100" not in aligned


def test_story_sentence_replaces_a_score_that_is_not_the_sealed_overall():
    story = "Acme scores 78/100 (grade B). This figure is the weighted rollup of pillar scores."
    aligned = align_story_score(story, 68, 68.0)
    assert aligned.startswith("Acme scores 68.0/100 (grade C).")
    assert "78/100" not in aligned
    assert "grade B" not in aligned


def test_story_match_rejects_a_headline_that_is_not_the_composite():
    story = "Enterprise Platform scores 78/100 (grade B)."
    assert story_matches_composite(story, 68.0) is False
    assert story_matches_composite(story, 80.0) is False
    assert story_matches_composite("No score in this sentence.", 80.0) is True
    assert story_matches_composite("Enterprise Platform scores 68.0/100 (grade C).", 68.0) is True


def test_serp_copy_does_not_invent_a_period_on_a_fragment():
    source = "Discover pricing from Acme for teams who need a complete explanation of the rollout plan and the support model before they buy today please continue"
    fitted = fit_serp_text(source, 160)
    assert len(fitted) <= 160
    assert not fitted.endswith(".") or source[: len(fitted)].rstrip().endswith(".")


def test_disconnected_google_channels_have_no_metrics():
    sealed = collect_google_performance(
        "example.com",
        search_console_loader=lambda domain: {
            "status": "unavailable",
            "reason": "not_connected",
            "is_connected": False,
            "total_monthly_clicks": 0,
            "total_monthly_impressions": 0,
        },
        analytics_loader=lambda domain: {"provenance": "NOT_CONFIGURED", "sessions_30d": 0, "status_notice": "not connected"},
    )
    assert sealed["search_console"]["state"] == "NOT_CONNECTED"
    assert "clicks" not in sealed["search_console"]
    assert sealed["analytics"]["state"] == "NOT_CONNECTED"
    assert "sessions" not in sealed["analytics"]


def test_measured_search_console_keeps_the_fetched_values():
    channel = map_search_console({
        "status": "authenticated",
        "is_connected": True,
        "total_monthly_clicks": 12,
        "total_monthly_impressions": 340,
        "average_ctr": 3.53,
        "average_position": 9.1,
        "top_ranking_keywords": [{
            "query": "widget",
            "target_page": "/",
            "monthly_clicks": 12,
            "monthly_impressions": 340,
            "ctr_percentage": 3.53,
            "current_position": 9.1,
        }],
        "provenance": {"property": "sc-domain:example.com", "date_range": "28d"},
    })
    assert channel["state"] == "MEASURED"
    assert channel["clicks"] == 12
    assert channel["property"] == "sc-domain:example.com"
    assert channel["queries"][0]["query"] == "widget"


def test_analytics_payload_without_sessions_is_no_data():
    channel = map_analytics({
        "state": "PAYLOAD",
        "property_id": "123",
        "payload": {"metricHeaders": [{"name": "bounceRate"}], "rows": [{"metricValues": [{"value": "0.4"}]}]},
    })
    assert channel["state"] == "NO_DATA"
    assert "sessions" not in channel


def test_expired_search_console_is_not_authorized():
    channel = map_search_console({
        "status": "unavailable",
        "is_connected": False,
        "reason": "401 token expired",
        "total_monthly_clicks": 0,
    })
    assert channel["state"] == "NOT_AUTHORIZED"
    assert "clicks" not in channel
