"""Tests for Phase 0: Canonical Enterprise Scorecard Engine & 5-PDF Score Consistency."""
from types import SimpleNamespace

from app.scoring.canonical_scorecard import (
    METHODOLOGY_VERSION,
    PILLAR_CAPABILITY_WEIGHTS,
    PILLAR_WEIGHTS,
    CanonicalScorecardEngine,
    CapabilityAssessment,
    CrawlCoverageFunnel,
    render_canonical_scorecard_html,
)


def test_weights_sum_to_100():
    assert sum(PILLAR_WEIGHTS.values()) == 100.0
    for pillar, caps in PILLAR_CAPABILITY_WEIGHTS.items():
        assert sum(caps.values()) == 100.0, f"{pillar} weights do not sum to 100"


def test_unmeasured_and_disconnected_never_pass_or_become_zero():
    funnel = CrawlCoverageFunnel(
        discovered_urls=505, crawled_urls=5, rendered_urls=2, inspected_urls=5, tested_urls=0
    )
    caps = [
        CapabilityAssessment(
            capability_id="technical_seo",
            pillar="SEO",
            weight=15.0,
            status="MEASURED",
            acceptance_passed=True,
            measured_score=80.0,
            evidence_count=5,
        ),
        # Disconnected connector tries to claim acceptance_passed=True -> engine MUST reject
        CapabilityAssessment(
            capability_id="backlink_intelligence",
            pillar="SEO",
            weight=10.0,
            status="NOT_CONNECTED",
            acceptance_passed=True,
            measured_score=100.0,
            provider="DataForSEO",
        ),
    ]
    card = CanonicalScorecardEngine.compute(
        audit_run_id="run_test_01",
        domain="perforacare.com",
        crawl_coverage=funnel,
        capability_inputs=caps,
    )
    assert card.methodology_version == METHODOLOGY_VERSION
    assert card.crawl_coverage.discovered_urls == 505
    assert card.crawl_coverage.crawled_urls == 5
    assert card.crawl_coverage.coverage_pct == 1.0
    assert card.crawl_coverage.scope_label == "SAMPLED_AUDIT"

    seo = card.pillars["SEO"]
    # Only technical_seo (80.0) is measured; backlink_intelligence is NOT_CONNECTED so excluded
    assert seo.measured_health_score == 80.0
    assert seo.measured_capabilities == 1
    assert seo.capability_completeness_score == 15.0
    bl_cap = next(c for c in seo.capabilities if c.capability_id == "backlink_intelligence")
    assert bl_cap.acceptance_passed is False
    assert bl_cap.measured_score is None
    assert card.optimization_effectiveness_score is None
    assert card.optimization_effectiveness_status == "NOT_ENOUGH_DATA"
    assert len(card.scorecard_sha256) == 64


def test_same_report_yields_identical_seal_across_all_5_pdf_views():
    report = SimpleNamespace(
        analysis_id="an_perfora_01",
        domain="perforacare.com",
        crawl_manifest=SimpleNamespace(
            total_pages_discovered=505,
            pages=[SimpleNamespace(url=f"https://perforacare.com/p{i}", rendered_dom=True) for i in range(5)],
        ),
        scores=SimpleNamespace(
            category_scores={
                "TECHNICAL_SEO": SimpleNamespace(score=72.0, status="MEASURED"),
                "ON_PAGE_SEO": SimpleNamespace(score=68.0, status="MEASURED"),
                "UX_CONVERSION": SimpleNamespace(score=67.5, status="MEASURED"),
            }
        ),
        geo_readiness=SimpleNamespace(extractability_score=64.0),
    )
    c1 = CanonicalScorecardEngine.evaluate_from_report(report)
    c2 = CanonicalScorecardEngine.evaluate_from_report(report)
    assert c1.scorecard_sha256 == c2.scorecard_sha256

    for family in ("SEO", "GEO", "AEO", "CRO", "COMPLETE"):
        html_block = render_canonical_scorecard_html(c1, pillar_filter=family)
        assert c1.scorecard_sha256[:16] in html_block
        assert "505" in html_block
        assert "NOT ENOUGH DATA" in html_block
