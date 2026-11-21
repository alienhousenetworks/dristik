"""Customer-facing scores count only observations that were actually made."""
from types import SimpleNamespace

import pytest

from app.domain.enums import BusinessIntent, Category, Severity
from app.domain.models import BusinessProfile, Finding, PageEvidence
from app.report_integrity_gate import validate_final_report
from app.scoring.engine import ScoringEngine


def _profile() -> BusinessProfile:
    return BusinessProfile(business_name="Acme", domain="acme.example", primary_intent=BusinessIntent.SAAS)


def _engine() -> ScoringEngine:
    return ScoringEngine()


def test_a_check_with_no_observation_is_not_a_pass():
    result = _engine().calculate_scores(findings=[], business_profile=_profile())
    technical = result.category_scores[Category.TECHNICAL_SEO.value]
    assert technical.status == "NOT_MEASURED"
    assert technical.score is None
    for check in technical.check_results:
        assert check.status == "NOT_MEASURED"
        assert check.sample_size == 0
        assert check.passed == 0


def test_one_cited_url_does_not_mark_the_rest_of_the_crawl_passed():
    finding = Finding(
        finding_id="title_1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Missing title tag",
        description="The pricing URL has no title.",
        recommendation="Add a title.",
        affected_urls=["https://acme.example/pricing", "https://acme.example/about"],
    )
    result = _engine().calculate_scores(
        findings=[finding],
        business_profile=_profile(),
        audit_scope=SimpleNamespace(plan_tier="starter", measured_pages=20, requested_pages=20, discovered_urls=[]),
    )
    checks = {item.check_id: item for item in result.category_scores[Category.ON_PAGE_SEO.value].check_results}
    title = checks["title_present"]
    assert title.sample_size == 2
    assert title.passed == 0
    assert title.failed == 2
    assert title.score == 0.0


def test_page_fields_count_passes_and_fails():
    pages = [
        PageEvidence(url="https://acme.example/", title="Home", meta_description="", h1=["Home"]),
        PageEvidence(url="https://acme.example/pricing", title="", meta_description="Plans", h1=[]),
    ]
    result = _engine().calculate_scores(findings=[], business_profile=_profile(), pages=pages)
    checks = {item.check_id: item for item in result.category_scores[Category.ON_PAGE_SEO.value].check_results}
    assert checks["title_present"].sample_size == 2
    assert checks["title_present"].passed == 1
    assert checks["title_present"].failed == 1
    assert checks["single_h1_present"].passed == 1
    assert checks["single_h1_present"].failed == 1


def test_missing_fact_precision_is_not_seven_of_ten():
    result = _engine().calculate_scores(
        findings=[],
        business_profile=_profile(),
        live_citation_score=70,
        live_benchmark_data={"ai_answer_diff": {"verified_claims": 1}},
    )
    checks = {item.check_id: item for item in result.category_scores[Category.AI_SEARCH.value].check_results}
    fact = checks["ai_fact_precision_recall"]
    assert fact.status == "NOT_MEASURED"
    assert fact.sample_size == 0
    assert fact.passed == 0


def test_citation_ready_requires_a_measured_live_run():
    honest = _engine().calculate_honest_scores(
        findings=[],
        business_profile=_profile(),
        is_https=True,
        readability=55.0,
    )
    assert honest.ai_visibility_status == "NOT_MEASURED"
    assert honest.score_band != "Citation Ready"
    assert honest.score_band != "Category Benchmark"

    cited = _engine().calculate_honest_scores(
        findings=[],
        business_profile=_profile(),
        is_https=True,
        readability=55.0,
        live_citation_score=80,
    )
    assert cited.ai_visibility_status == "MEASURED"
    if cited.overall_score is not None and cited.overall_score >= 75:
        assert cited.score_band in {"Citation Ready", "Category Benchmark"}


def test_buyer_simulation_does_not_change_ai_readiness():
    bare = _engine().calculate_honest_scores(findings=[], business_profile=_profile(), readability=55.0)
    simulated = _engine().calculate_honest_scores(
        findings=[],
        business_profile=_profile(),
        readability=55.0,
        commercial_evals=[SimpleNamespace(before_score=9), SimpleNamespace(before_score=2)],
    )
    assert simulated.ai_readiness_score == bare.ai_readiness_score


def test_synthetic_evidence_hash_blocks_certification():
    report = SimpleNamespace(
        findings=[SimpleNamespace(
            finding_id="f1",
            title="Missing title",
            category="ON_PAGE_SEO",
            evidence_refs=["ev_det_000"],
            evidence=[],
        )],
        evidence_ledger={
            "ev_det_000": {
                "id": "ev_det_000",
                "content_sha256": "sha_ev_det_000",
                "hash": "hash_ev_det_000",
            }
        },
        scores=SimpleNamespace(overall_score=0, category_scores={}),
        analysis_id="run-1",
        report_id="rep-1",
    )
    with pytest.raises(ValueError, match="SHA-256"):
        validate_final_report(report)
