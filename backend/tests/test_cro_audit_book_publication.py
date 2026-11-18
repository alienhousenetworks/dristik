"""
Tests for Phase 6.11: Publication-Grade CRO Audit Book & SVG Visuals.
"""
import pytest
from app.domain.models import PageEvidence
from app.cro.cro_chapter_visuals import (
    cro_ten_dimension_scorecard_svg,
    cro_journey_flow_svg,
    cro_cta_contrast_matrix_svg,
)
from app.reports.adaptive_audit_book import (
    build_adaptive_publication_document,
    detect_report_family,
)
from app.cro.reporting import render_cro_audit_book
from types import SimpleNamespace


def test_cro_svg_visuals_generate_valid_xml():
    scorecard_svg = cro_ten_dimension_scorecard_svg([
        {"name": "Value Proposition", "score": 85.0, "status": "MEASURED"},
        {"name": "Visual Hierarchy", "score": 90.0, "status": "MEASURED"},
        {"name": "Behavioural Analytics", "score": None, "status": "UNMEASURED"},
    ])
    assert "<svg" in scorecard_svg
    assert "</svg>" in scorecard_svg
    assert "UNMEASURED" in scorecard_svg

    journey_svg = cro_journey_flow_svg()
    assert "<svg" in journey_svg
    assert "VISUAL USER CONVERSION JOURNEY MAP" in journey_svg

    cta_svg = cro_cta_contrast_matrix_svg(4, 6, 2)
    assert "<svg" in cta_svg
    assert "High Intent" in cta_svg


def test_cro_audit_book_renders_all_10_chapters():
    p = PageEvidence(
        url="https://example.com/",
        title="Test Store",
        h1=["Scale With Automated Intelligence"],
        word_count=200,
        ctas=["Get Started Now"],
    )
    report = SimpleNamespace(
        domain="example.com",
        website_url="https://example.com",
        generated_at="2026-11-18T10:00:00Z",
        analysis_id="cro_test_001",
        crawl_manifest=SimpleNamespace(pages=[p], total_pages_discovered=5),
        cro_audit=SimpleNamespace(
            overall_cro_score=82.0,
            cro_grade="B",
            primary_cta_text="Get Started Now",
            ctas=[],
            trust_signals=[],
            value_prop=SimpleNamespace(hero_headline="Scale With Automated Intelligence"),
            form_friction=None,
        ),
        scores=SimpleNamespace(overall_score=82.0, evidence_coverage=0.9),
        contradictions=[],
        policy_pack="cro_audit",
    )

    doc = build_adaptive_publication_document(report, report_type="CRO")
    assert doc.metadata.family == "CRO"

    all_chapters = [ch.id for part in doc.parts for ch in part.chapters]
    cro_chapters = [ch.id for part in doc.parts for ch in part.chapters if ch.id.startswith("ch_cro_")]
    assert len(cro_chapters) == 10
    assert "ch_cro_value_prop" in all_chapters
    assert "ch_cro_visual_hierarchy" in all_chapters
    assert "ch_cro_cta" in all_chapters
    assert "ch_cro_journey" in all_chapters
    assert "ch_cro_forms" in all_chapters
    assert "ch_cro_mobile" in all_chapters
    assert "ch_cro_accessibility" in all_chapters
    assert "ch_cro_trust" in all_chapters
    assert "ch_cro_checkout" in all_chapters
    assert "ch_cro_experiments" in all_chapters

    html_out = render_cro_audit_book(report)
    assert len(html_out) > 5000
    assert "Multi-Device Visual Inspection" in html_out
    assert "Visual User Journey Graph" in html_out
    assert "Statistical Experimentation Roadmap" in html_out
