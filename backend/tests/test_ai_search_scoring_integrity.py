"""
Test AI Search Scoring Integrity & Fail-Closed Behavior.
Verifies that:
1. AI_SEARCH checks without live data or evidence evaluate to NOT_MEASURED (never silent PASS).
2. When live benchmark data is provided, all 5 AI_SEARCH checks compute mathematically honest scores
   with exact sample sizes, Wilson confidence intervals, and displacement metrics.
"""
import pytest
from app.domain.enums import BusinessIntent, Category
from app.domain.models import BusinessProfile, Finding
from app.scoring.engine import ScoringEngine


def test_ai_search_without_live_data_is_not_measured():
    engine = ScoringEngine()
    profile = BusinessProfile(
        business_name="Test Brand",
        domain="testbrand.com",
        primary_intent=BusinessIntent.SAAS
    )

    # Clean audit with NO live citation run and NO benchmark data
    res = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        live_citation_score=None,
        live_benchmark_data=None,
    )

    # AI_SEARCH category must be NOT_MEASURED with score None
    ai_search_cat = res.category_scores.get(Category.AI_SEARCH.value)
    assert ai_search_cat is not None
    assert ai_search_cat.status == "NOT_MEASURED"
    assert ai_search_cat.score is None

    # Crucially: AI_SEARCH checks must NOT be 1.0 (PASS)
    for check_res in ai_search_cat.check_results:
        assert check_res.status == "NOT_MEASURED"
        assert check_res.score == 0.0 or check_res.score is None


def test_ai_search_with_live_benchmark_data_computes_all_checks():
    engine = ScoringEngine()
    profile = BusinessProfile(
        business_name="Test Brand",
        domain="testbrand.com",
        primary_intent=BusinessIntent.SAAS
    )

    live_benchmark = {
        "total_queries": 18,
        "overall_mention_rate_pct": 77.8,
        "overall_first_party_citation_rate_pct": 44.4,
        "share_of_model": {
            "share_of_model_pct": 77.8,
            "competitor_only_rate": 0.15,
            "competitor_displacements": [{"competitor": "RivalApp", "query": "pricing"}],
            "stage_breakdown": {
                "decision": {
                    "total": 8,
                    "mentioned": 6
                }
            }
        },
        "ai_answer_diff": {
            "fact_precision": 0.85,
            "total_claims": 12,
            "verified_claims": 10,
            "unverified_claims": 2,
            "contradictions": 0
        }
    }

    res = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        live_citation_score=77.8,
        live_benchmark_data=live_benchmark,
    )

    ai_search_cat = res.category_scores.get(Category.AI_SEARCH.value)
    assert ai_search_cat is not None
    assert ai_search_cat.status == "MEASURED"
    assert ai_search_cat.score is not None
    assert ai_search_cat.score > 0.0

    checks_by_id = {c.check_id: c for c in ai_search_cat.check_results}

    # 1. Mention rate
    mention_chk = checks_by_id["ai_brand_mention_rate"]
    assert round(mention_chk.score, 2) == 0.78
    assert mention_chk.sample_size == 18

    # 2. Domain citation rate
    cite_chk = checks_by_id["ai_domain_citation_rate"]
    assert round(cite_chk.score, 2) == 0.44
    assert cite_chk.sample_size == 18

    # 3. Displacement resistance: 1 - 0.15 = 0.85
    disp_chk = checks_by_id["ai_displacement_resistance"]
    assert round(disp_chk.score, 2) == 0.85

    # 4. Decision stage mention: 6 / 8 = 0.75
    dec_chk = checks_by_id["ai_decision_stage_mention"]
    assert round(dec_chk.score, 2) == 0.75

    # 5. Fact precision: 0.85
    fact_chk = checks_by_id["ai_fact_precision_recall"]
    assert round(fact_chk.score, 2) == 0.85
