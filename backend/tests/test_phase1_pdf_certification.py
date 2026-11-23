from app.seo.reporting.enterprise_pdf_engine import EnterprisePdfEngine
from app.seo.reporting.seo_chapter_registry import MASTER_9_APPENDICES
from app.seo.reporting.enterprise_pdf_engine import QaCertificationReport


def test_missing_qa_is_not_certified_in_appendix():
    engine = EnterprisePdfEngine()
    appendix = next(chapter for chapter in MASTER_9_APPENDICES if chapter.id == "app_I")
    html = engine._render_appendix_body(
        appendix,
        {
            "limitations": [],
            "qa": None,
        },
    )
    assert "NOT_CERTIFIED" in html
    assert "<code>CERTIFIED</code>" not in html


def test_missing_qa_renders_draft_not_certified_banner():
    engine = EnterprisePdfEngine()
    report_data = {
        "analysis_id": "test_qa_failclosed",
        "domain": "acme.test",
        "findings": [],
        "crawl_manifest": {"pages": []},
        "scorecard": {"overall_health_score": None, "dimensions": []},
        "tasks": [],
    }
    html = engine.render_publication(
        assessment=None,
        report_data=report_data,
        profile="complete_book",
        qa_report=None,
    )
    assert "DRAFT — NOT CERTIFIED" in html
    assert "qa-banner-blocked" in html


def test_explicit_certification_status_is_preserved():
    engine = EnterprisePdfEngine()
    qa = QaCertificationReport(
        audit_id="test_qa_certified",
        is_certified=True,
        status="CERTIFIED",
        blockers_count=0,
        warnings_count=0,
        gate_results=[],
        blocking_reasons=[],
    )
    report_data = {
        "analysis_id": "test_qa_certified",
        "domain": "acme.test",
        "findings": [],
        "crawl_manifest": {"pages": []},
        "scorecard": {"overall_health_score": 85.0, "dimensions": []},
        "tasks": [],
    }
    html = engine.render_publication(
        assessment=None,
        report_data=report_data,
        profile="complete_book",
        qa_report=qa,
    )
    assert '<div class="qa-banner-blocked">' not in html
    assert "DRAFT — NOT CERTIFIED" not in html
