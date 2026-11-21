import pytest
from app.seo.reporting.seo_chapter_registry import (
    MASTER_63_CHAPTERS,
    MASTER_9_APPENDICES,
    get_chapters_for_profile,
)
from app.seo.reporting.enterprise_pdf_engine import EnterprisePdfEngine

def test_chapter_registry_count_and_profiles():
    assert len(MASTER_63_CHAPTERS) == 63
    assert len(MASTER_9_APPENDICES) == 9

    # Complete book profile includes all 72 chapters & appendices
    complete_book = get_chapters_for_profile("complete_book")
    assert len(complete_book) == 72

    # Executive brief is concise
    exec_brief = get_chapters_for_profile("executive")
    assert 5 <= len(exec_brief) <= 25

    # Technical report focuses on technical & remediation
    tech_report = get_chapters_for_profile("technical")
    assert len(tech_report) >= 20

def test_enterprise_pdf_engine_render():
    engine = EnterprisePdfEngine()
    assessment_mock = type("MockAssessment", (), {
        "findings": [{"finding_id": "SEO_FND_01", "severity": "CRITICAL", "title": "Test Defect"}],
        "coverage": {
            "urls_discovered": 505,
            "urls_crawled": 5,
            "urls_rendered": 5,
            "urls_deeply_inspected": 5,
            "urls_with_verified_findings": 1,
        },
    })()

    html_out = engine.render_publication(
        assessment=assessment_mock,
        report_data={"domain": "perforacare.com", "analysis_id": "PERF_001"},
        profile="complete_book",
    )

    assert "<!DOCTYPE html>" in html_out
    assert "perforacare.com" in html_out
    assert "Table of Contents" in html_out
    assert "505 URLs" in html_out
    assert "Test Defect" in html_out
    assert "PASS (No regression blockers)" not in html_out
    assert "Chapter 18" in html_out  # Technical SEO


def test_enterprise_pdf_does_not_invent_coverage_or_a_pass():
    engine = EnterprisePdfEngine()
    html_out = engine.render_publication(
        assessment=None,
        report_data={"domain": "empty.example", "analysis_id": "EMPTY"},
        profile="executive",
    )
    assert "505 URLs" not in html_out
    assert "Not measured" in html_out
    assert "NOT TESTED" in html_out
    assert "96%" not in html_out
