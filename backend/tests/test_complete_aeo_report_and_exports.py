"""
Unit & Integration Tests for Complete AEO Report & CSV Exports (2026 Master Standard)
"""
import pytest
from fastapi.testclient import TestClient

from app.domain.enums import Category, FindingStatus, Severity
from app.domain.models import (
    AiVisibilityScorecard,
    BusinessProfile,
    ExecutiveReport,
    Finding,
    GeoQuestionEvidence,
    GeoReadinessReport,
    OverallScoreResult,
    PageReport,
    ThreeWayComparison,
)
from app.reports.export_service import (
    generate_aeo_remediation_csv,
    generate_aeo_question_dataset_csv,
)
from app.reports.aeo_report_generator import aeo_report_generator


def _make_dummy_aeo_report() -> ExecutiveReport:
    """Helper to build a valid ExecutiveReport fixture with AEO question data."""
    page_1 = PageReport(
        url="https://acme.com",
        title="Acme Corp - Enterprise Workflow & AI Solutions",
        meta_description="Acme provides enterprise AI workflow software and cloud automation systems.",
        status_code=200,
        word_count=850,
        h1_tags=["Enterprise AI Workflow Automation"],
        schema_types=["Organization", "FAQPage"],
        ttfb_ms=180.0,
    )

    finding_1 = Finding(
        finding_id="ANS-001",
        category=Category.CONTENT,
        subcategory="Direct Answer Passage Omission",
        affected_urls=["https://acme.com"],
        expected_condition="Primary capability summarized in a concise 40-60 word definition passage directly under matching H2.",
        dependencies=["Commercial Copywriting", "FAQ Template"],
        status=FindingStatus.OPEN,
        owner="Answer Content & SEO Engineering",
        severity=Severity.HIGH,
        title="Missing Direct Definition Answer Passage for Workflow Automation",
        description="The homepage lacks a self-contained 40-60 word definition block for workflow automation.",
        recommendation="Deploy an explicit answer definition paragraph directly below the H2 question heading.",
        why_it_matters="Featured snippets and AI engines fail to extract direct answers, citing competitors instead.",
        validation_criteria="Automated re-crawl confirms passage extractability and zero entity contradiction.",
        priority=8,
        impact=9,
        effort=3,
        confidence=0.88,
        confidence_basis="Observed DOM Crawl & Passage Extractor",
    )

    geo_readiness = GeoReadinessReport(
        entity_name="Acme Corp",
        headline="Strong technical foundation with direct answer definition and pricing passage gaps.",
        extractability_score=84.0,
        questions_total=4,
        questions_supported=2,
        questions_partial=1,
        questions_unsupported=1,
        schema_types=["Organization", "FAQPage"],
        questions=[
            GeoQuestionEvidence(
                question_key="Q-DISC-01",
                question="What is Acme Corp and how does workflow automation work?",
                status="SUPPORTED",
                answer="Acme Corp provides automated workflow orchestration for enterprise teams.",
                answer_snippet="Acme provides enterprise AI workflow software.",
                recommended_answer="Maintain concise definition under primary H2 heading.",
            ),
            GeoQuestionEvidence(
                question_key="Q-COMP-02",
                question="How does Acme compare to Zapier and Workato?",
                status="PARTIAL",
                answer="Acme operates across multi-cloud infrastructure.",
                answer_snippet="Multi-cloud infrastructure support.",
                recommended_answer="Deploy objective comparison table with feature rows.",
            ),
            GeoQuestionEvidence(
                question_key="Q-PRIC-03",
                question="How much does Acme enterprise workflow automation cost?",
                status="UNSUPPORTED",
                answer="",
                answer_snippet="",
                recommended_answer="Publish explicit starter pricing tiers and billing models.",
            ),
        ],
    )

    visibility_scorecard = AiVisibilityScorecard(
        status="NOT_MEASURED",
        measurement_note="Live visibility requires connected search engine credentials. Direct observations not yet recorded.",
        engines_measured=0,
        queries=0,
    )

    return ExecutiveReport(
        report_id="rep_aeo_test_001",
        analysis_id="analysis_aeo_test_001",
        website_url="https://acme.com",
        domain="acme.com",
        generated_at="October 10, 2026 - 12:00 UTC",
        business_profile=BusinessProfile(business_name="Acme Corp"),
        scores=OverallScoreResult(overall_score=82.0, grade="B", health_label="Good"),
        story_summary="Acme Corp demonstrates solid content structure with actionable featured snippet and transactional answer gaps.",
        primary_strategic_opportunity="Publish authoritative competitor comparison tables and explicit pricing policies.",
        consultant_advice_what_to_ignore="Ignore keyword stuffing and redundant doorway FAQ pages.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear value proposition.",
            search_engine_perspective="Clean crawl indexability.",
            ai_answer_engine_perspective="Good entity structure.",
        ),
        findings=[finding_1],
        page_reports=[page_1],
        geo_readiness=geo_readiness,
        ai_visibility_scorecard=visibility_scorecard,
        ai_visibility_score=None,
    )


def test_aeo_json_report_covers_all_20_sections():
    report = _make_dummy_aeo_report()
    json_data = aeo_report_generator.render_json_report(report)

    assert json_data["domain"] == "acme.com"
    assert json_data["analysis_id"] == "analysis_aeo_test_001"
    assert json_data["report_type"] == "AEO_MASTER_AUDIT_2026"

    # KPI checks
    kpis = json_data["kpis"]
    assert kpis["answer_readiness_score"] == 84.0
    assert kpis["observed_visibility_status"] == "NOT_MEASURED"
    assert kpis["questions_evaluated"] == 4
    assert kpis["questions_supported"] == 2

    # Check that sections 01 through 20 are all present
    sections = json_data["sections"]
    expected_section_keys = [
        "01_executive_summary",
        "02_audit_scope_and_methodology",
        "03_question_universe_and_intent_mapping",
        "04_answer_readiness_and_content_structure",
        "05_featured_snippet_analysis",
        "06_people_also_ask_and_related_questions",
        "07_faq_and_question_answer_content_audit",
        "08_structured_data_and_rich_results",
        "09_entity_answers_and_knowledge_panels",
        "10_voice_and_conversational_search",
        "11_ai_answer_engine_visibility",
        "12_local_and_action_oriented_answers",
        "13_product_commercial_and_transactional_answers",
        "14_support_documentation_and_troubleshooting",
        "15_answer_accuracy_and_source_quality",
        "16_competitor_answer_benchmarking",
        "17_search_performance_and_business_outcomes",
        "18_content_gaps_and_answer_strategy",
        "19_prioritized_remediation_roadmap",
        "20_appendices_and_evidence_register",
    ]
    for key in expected_section_keys:
        assert key in sections, f"Section '{key}' missing from rendered JSON report."

    # Verify intent mapping
    q_map = sections["03_question_universe_and_intent_mapping"]["questions_mapped"]
    assert len(q_map) >= 3
    assert any(q["question_type"] == "What" for q in q_map)
    assert any(q["question_type"] == "How" for q in q_map)


def test_aeo_html_report_rendering_integrity():
    report = _make_dummy_aeo_report()
    html_output = aeo_report_generator.render_html_report(report)

    assert "<!DOCTYPE html>" in html_output
    assert "Complete AEO Master Audit &amp; Answer Engine Optimization Report - acme.com" in html_output or "acme.com" in html_output

    # Verify all 20 section anchor tags exist
    for sec_id, _ in aeo_report_generator.SECTIONS:
        assert f'id="{sec_id}"' in html_output, f"Anchor id '{sec_id}' missing in HTML output."
        assert f'href="#{sec_id}"' in html_output, f"Navigation link href='#{sec_id}' missing in sidebar."

    # Verify 10 domains grid rendered
    assert "The 10 Core Domains of Answer Engine Optimization" in html_output
    assert "Featured Snippet Optimization" in html_output
    assert "Voice Search &amp; Conversational Answers" in html_output or "Voice Search & Conversational Answers" in html_output

    # Verify standardized 14-field AEO finding card
    assert "AEO-ANS-001" in html_output
    assert "Missing Direct Definition Answer Passage" in html_output
    assert "Reference Baseline / Expected Condition" in html_output
    assert "Potential Impact on Answer Visibility" in html_output
    assert "Prescriptive AEO Recommendation" in html_output
    assert "Verification Acceptance Criteria" in html_output

    # Verify disclaimers & core rule
    assert "Core AEO Architecture Rule: Separation of Outcomes" in html_output
    assert "Answer Readiness" in html_output
    assert "Observed Answer Appearances" in html_output


def test_aeo_remediation_csv_export():
    report = _make_dummy_aeo_report()
    csv_data = generate_aeo_remediation_csv(report)

    assert "Finding ID,AEO Domain,Subcategory" in csv_data
    assert "AEO-ANS-001" in csv_data
    assert "Missing Direct Definition Answer Passage" in csv_data
    assert "Answer Content & SEO Engineering" in csv_data
    assert "Fixed vs Verified" in csv_data


def test_aeo_question_dataset_csv_export():
    report = _make_dummy_aeo_report()
    csv_data = generate_aeo_question_dataset_csv(report)

    assert "Question Key,Target Question,Question Type" in csv_data
    assert "Q-DISC-01" in csv_data
    assert "What is Acme Corp and how does workflow automation work?" in csv_data
    assert "SUPPORTED" in csv_data
    assert "UNSUPPORTED" in csv_data


def test_aeo_report_fastapi_endpoints():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock
    from app.main import app
    from app.orchestration.orchestrator import orchestrator

    client = TestClient(app)
    mock_run = MagicMock()
    mock_run.report = _make_dummy_aeo_report()
    mock_run.created_at = "2026-10-10"
    mock_run.domain = "acme.com"
    mock_run.website_url = "https://acme.com"

    original_get_run = orchestrator.get_run
    orchestrator.get_run = MagicMock(return_value=mock_run)

    try:
        # 1. HTML AEO Report
        res_html = client.get("/api/v1/reports/analysis_aeo_test_001/aeo-report?format=html")
        assert res_html.status_code == 200
        assert "text/html" in res_html.headers["content-type"]
        assert "Complete AEO Master Audit" in res_html.text

        # 2. JSON AEO Report
        res_json = client.get("/api/v1/reports/analysis_aeo_test_001/aeo-report?format=json")
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["report_type"] == "AEO_MASTER_AUDIT_2026"
        assert len(data["sections"]) == 20

        # 3. CSV AEO Remediation Tracker Export
        res_csv = client.get("/api/v1/reports/analysis_aeo_test_001/export/aeo-remediation-tracker.csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "AEO-ANS-001" in res_csv.text
        assert 'filename="acme.com_aeo_remediation_tracker.csv"' in res_csv.headers["content-disposition"]

        # 4. CSV AEO Question Dataset Export
        res_q_csv = client.get("/api/v1/reports/analysis_aeo_test_001/export/aeo-question-dataset.csv")
        assert res_q_csv.status_code == 200
        assert "text/csv" in res_q_csv.headers["content-type"]
        assert "Q-DISC-01" in res_q_csv.text
        assert 'filename="acme.com_aeo_question_dataset.csv"' in res_q_csv.headers["content-disposition"]
    finally:
        orchestrator.get_run = original_get_run
