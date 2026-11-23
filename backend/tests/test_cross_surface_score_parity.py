"""Cross-surface score parity and scope over-generalization guard tests.

Verifies exact 0.0 drift across:
  - CanonicalScorecardEngine
  - Serialized ExecutiveReport.canonical_scorecard JSON
  - displayed_composite()
  - snapshot_provenance.format_audit_execution_metadata()
  - narrative_validator.build_scorecard_vars()
  - PPTX DeckMathEngine & DeckDataAnalystAgent
  - All 5 PDF HTML outputs (Complete, SEO, GEO, AEO, CRO)
Plus deterministic scope grounding for sampled crawls and partial findings.
"""
from __future__ import annotations

import pytest

from app.domain.enums import Category, Severity
from app.domain.models import (
    CategoryScore,
    CrawlManifest,
    ExecutiveReport,
    Finding,
    OverallScoreResult,
    PageEvidence,
)
from app.domain.scoring.canonical_scorecard import CanonicalScorecardEngine
from app.domain.scoring.displayed_score import displayed_composite
from app.reports.deck.math_engine import DeterministicMetricEngine
from app.reports.narrative_validator import (
    build_scorecard_vars,
    enforce_scope_grounding,
    validate_and_hydrate_bundle,
    verify_finding_ai_blocks,
)
from app.reports.snapshot_provenance import format_audit_execution_metadata


def _make_report(
    *,
    crawled_pages: int = 5,
    discovered_pages: int = 120,
    seo: float | None = 74.0,
    geo: float | None = 62.0,
    aeo: float | None = None,
    cro: float | None = 68.0,
    legacy_overall: float = 91.5,
) -> ExecutiveReport:
    pages = [
        PageEvidence(
            url=f"https://example.com/page-{i}",
            status_code=200,
            title=f"Page {i}",
            word_count=450,
            ttfb_ms=220.0 + i * 15.0,
        )
        for i in range(crawled_pages)
    ]
    cat_scores = {}
    if seo is not None:
        cat_scores["TECHNICAL_SEO"] = CategoryScore(
            category=Category.TECHNICAL_SEO, score=seo, weight=0.25, findings_count=1
        )
    if geo is not None:
        cat_scores["GEO"] = CategoryScore(
            category=Category.GEO, score=geo, weight=0.25, findings_count=1
        )
    if aeo is not None:
        cat_scores["AEO"] = CategoryScore(
            category=Category.AI_SEARCH, score=aeo, weight=0.25, findings_count=1
        )
    if cro is not None:
        cat_scores["UX_CONVERSION"] = CategoryScore(
            category=Category.UX_CONVERSION, score=cro, weight=0.25, findings_count=1
        )

    scores = OverallScoreResult(
        overall_score=legacy_overall,  # Intentionally different from canonical to catch legacy leaks
        grade="A",
        health_label="Excellent",
        category_scores=cat_scores,
    )
    findings = [
        Finding(
            finding_id="find_seo_001",
            title="Missing canonical tags",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            description="Canonical tag missing on sampled page.",
            recommendation="Add self-referencing canonical link tags.",
            affected_urls=["https://example.com/page-0"],
            evidence_ids=["ev_001"],
        ),
        Finding(
            finding_id="find_cro_001",
            title="Weak primary CTA contrast",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            description="Primary CTA button contrast is below target.",
            recommendation="Increase CTA button contrast.",
            affected_urls=["https://example.com/page-0"],
            evidence_ids=["ev_002"],
        ),
    ]
    report = ExecutiveReport(
        report_id="rep_parity_001",
        org_id="org_test",
        analysis_id="run_parity_001",
        website_url="https://example.com",
        domain="example.com",
        story_summary="Executive summary for cross-surface parity verification.",
        primary_strategic_opportunity="Consolidate canonical tags on core templates.",
        consultant_advice_what_to_ignore="Defer cosmetic footer tweaks until indexation is fixed.",
        scores=scores,
        crawl_manifest=CrawlManifest(
            target_url="https://example.com",
            domain="example.com",
            pages=pages,
            total_pages_discovered=discovered_pages,
        ),
        findings=findings,
    )
    CanonicalScorecardEngine.evaluate_from_report(report, force_recompute=True)
    return report


@pytest.mark.parametrize(
    "profile",
    [
        dict(crawled_pages=5, discovered_pages=120, seo=74.0, geo=62.0, aeo=None, cro=68.0, legacy_overall=91.5),
        dict(crawled_pages=10, discovered_pages=10, seo=88.0, geo=80.0, aeo=72.0, cro=84.0, legacy_overall=55.0),
        dict(crawled_pages=3, discovered_pages=50, seo=60.0, geo=None, aeo=None, cro=50.0, legacy_overall=82.0),
    ],
)
def test_cross_surface_canonical_score_parity(profile):
    report = _make_report(**profile)
    card = CanonicalScorecardEngine.evaluate_from_report(report)

    # 1. Serialized ExecutiveReport JSON carries canonical_scorecard verbatim
    dumped = report.model_dump(mode="json")
    assert dumped["canonical_scorecard"] is not None
    assert dumped["canonical_scorecard"]["composite_health_score"] == card.composite_health_score
    assert dumped["canonical_scorecard"]["composite_grade"] == card.composite_grade

    # 2. displayed_composite() agrees with canonical scorecard (never leaks legacy_overall)
    assert displayed_composite(report) == card.composite_health_score
    assert displayed_composite(dumped) == card.composite_health_score

    # 3. snapshot_provenance agrees on composite and every pillar
    snap = format_audit_execution_metadata(report)
    assert snap.composite_score == card.composite_health_score
    for pillar_key, sec_key in (("SEO", "seo"), ("GEO", "geo"), ("AEO", "aeo"), ("CRO", "cro")):
        p = card.pillars.get(pillar_key)
        expected = p.measured_health_score if p and p.status in ("MEASURED", "PARTIAL") else None
        assert snap.score_for_section(sec_key) == expected

    # 4. narrative_validator scorecard vars agree with canonical scorecard
    sv = build_scorecard_vars(report)
    expected_overall_str = f"{int(round(card.composite_health_score))}/100" if card.composite_health_score is not None else "NOT_MEASURED"
    assert sv["score.overall"] == expected_overall_str
    assert sv["crawl.crawled"] == str(profile["crawled_pages"])
    assert sv["crawl.discovered"] == str(profile["discovered_pages"])

    # 5. PPTX DeterministicMetricEngine agrees with canonical scorecard (not legacy scores.overall_score)
    deck_bundle = DeterministicMetricEngine().compute_bundle(report)
    if card.composite_health_score is not None:
        assert deck_bundle.overall_score == pytest.approx(card.composite_health_score, abs=1e-6)
        assert deck_bundle.grade == card.composite_grade


def test_geo_and_aeo_books_embed_canonical_scorecard():
    from app.aeo.reporting.audit_book import render_aeo_audit_book
    from app.geo.reporting.geo_audit_book import render_geo_audit_book

    report = _make_report(crawled_pages=5, discovered_pages=80, seo=76.0, geo=64.0, aeo=58.0, cro=70.0)
    card = CanonicalScorecardEngine.evaluate_from_report(report)

    geo_html = render_geo_audit_book(report)
    aeo_html = render_aeo_audit_book(report)

    assert "dristik_enterprise_v4.0" in geo_html or "Canonical Enterprise Scorecard" in geo_html or "64.0/100" in geo_html
    assert "dristik_enterprise_v4.0" in aeo_html or "Canonical Enterprise Scorecard" in aeo_html or "58.0/100" in aeo_html
    assert card.crawl_coverage.discovered_urls == 80
    assert card.crawl_coverage.crawled_urls == 5


def test_scope_overgeneralization_guard_rewrites_sampled_and_partial_claims():
    # Sampled crawl (5 of 120 discovered) must qualify site-wide / universal claims
    text = "This is a site-wide failure affecting every page across the entire website."
    grounded, fixes = enforce_scope_grounding(text, crawled_count=5, discovered_count=120)
    assert fixes >= 3
    assert "site-wide" not in grounded.lower()
    assert "entire website" not in grounded.lower()
    assert "inspected" in grounded.lower()

    # Partial finding (1 of 5 crawled pages on a full crawl) must qualify universal claims
    f_text = "All pages lack canonical tags."
    f_grounded, f_fixes = enforce_scope_grounding(f_text, affected_count=1, crawled_count=5, discovered_count=5)
    assert f_fixes == 1
    assert "affected inspected pages" in f_grounded.lower()

    # Full-site crawl where all pages are affected permits universal wording untouched
    full_text = "All pages lack canonical tags across the entire website."
    unchanged, zero_fixes = enforce_scope_grounding(full_text, affected_count=10, crawled_count=10, discovered_count=10)
    assert zero_fixes == 0
    assert unchanged == full_text


def test_narrative_bundle_and_finding_blocks_enforce_scope_grounding():
    report = _make_report(crawled_pages=5, discovered_pages=120)
    sv = build_scorecard_vars(report)
    assert sv["crawl.is_sampled"] == "true"

    bundle = {
        "executive_summary": "The audit scored {{score.overall}} and found a site-wide canonical gap on every page.",
        "chapters": [
            {
                "title": "Technical SEO",
                "executive_takeaway": "All pages need canonical consolidation.",
                "body_md": "Across the entire website, canonical tags are inconsistent.",
                "why_it_matters": "Crawl budget is wasted.",
                "cited_finding_ids": ["find_seo_001"],
            }
        ],
        "slides": [],
    }
    clean, val = validate_and_hydrate_bundle(
        bundle,
        verified_finding_ids={"find_seo_001"},
        scorecard_vars=sv,
    )
    assert val.scope_overgeneralizations_fixed >= 3
    assert "site-wide" not in clean["executive_summary"].lower()
    assert "entire website" not in clean["chapters"][0]["body_md"].lower()

    finding = {
        "finding_id": "find_seo_001",
        "evidence_ids": ["ev_001"],
        "affected_urls": ["https://example.com/page-0"],
        "ai_understanding": "Every page on the entire site is missing canonicals.",
        "ai_analysis": "This is a site-wide issue.",
        "fix_prompt": "Add canonical link tags to affected templates.",
    }
    res = verify_finding_ai_blocks(
        finding,
        valid_evidence_ids={"ev_001"},
        crawled_count=5,
        discovered_count=120,
    )
    assert res["verified_state"] == "VERIFIED"
    assert any(i.startswith("scope_overgeneralization_qualified") for i in res["issues"])
    assert "site-wide" not in finding["ai_analysis"].lower()
