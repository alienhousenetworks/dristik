"""Tests for Phase 11 — Rebuild the Report Experience (Layered Reporting)."""
from __future__ import annotations

import pytest

from app.reporting.layered import (
    EvidenceExplorerDTO,
    ExecutiveReportBuilder,
    ExecutiveReportData,
    FindingDetailPageBuilder,
    FindingDetailPageData,
    GeneratedDocumentArtifact,
    InteractiveEvidenceExplorer,
    LayeredReportGenerationEngine,
    LayeredReportingEngine,
    NarrativeQualityEngine,
    NarrativeQualityVerdict,
    ReportGenerationConfig,
    SpecialistDiscipline,
    SpecialistReportBuilder,
    SpecialistReportData,
)


def test_phase11_1_executive_report_all_12_sections():
    """Verify that the Executive Report synthesizes all 12 canonical sections."""
    builder = ExecutiveReportBuilder()

    findings = [
        {"title": "Uncached dynamic assets", "severity": "HIGH", "category": "TECHNICAL", "impact": "High server load."},
        {"title": "Missing title on category", "severity": "MEDIUM", "category": "SEO", "impact": "CTR loss."},
    ]

    report: ExecutiveReportData = builder.build_report(
        domain="enterprise-store.com",
        audit_id="aud_exp_11",
        client_name="Acme Corp",
        scores={"seo_score": 82.0, "geo_score": 68.0, "aeo_score": 70.0, "cro_score": 75.0, "tech_score": 88.0},
        findings=findings,
    )

    # 1. Cover and audit identity
    assert report.cover_and_identity["audit_id"] == "aud_exp_11"
    assert report.cover_and_identity["domain"] == "enterprise-store.com"
    assert report.cover_and_identity["client_name"] == "Acme Corp"
    assert report.cover_and_identity["certification_hash"]

    # 2. Executive summary
    assert "enterprise-store.com" in report.executive_summary
    assert "composite health index" in report.executive_summary

    # 3. Business profile
    assert report.business_profile["industry"]
    assert report.business_profile["primary_audience"]

    # 4. Scope and coverage
    assert report.scope_and_coverage["total_urls_crawled"] > 0
    assert report.scope_and_coverage["coverage_pct"] == 100.0

    # 5. Overall diagnostic status
    assert report.overall_diagnostic_status["composite_score"] > 0
    assert report.overall_diagnostic_status["health_rating"] in ("HEALTHY", "ATTENTION_REQUIRED", "CRITICAL")

    # 6. Top critical risks
    assert len(report.top_critical_risks) >= 1
    assert report.top_critical_risks[0]["severity"] == "HIGH"

    # 7. Top growth opportunities
    assert len(report.top_growth_opportunities) >= 3

    # 8. Five-pillar scorecard
    assert report.five_pillar_scorecard["seo"] == 82.0
    assert report.five_pillar_scorecard["geo"] == 68.0
    assert report.five_pillar_scorecard["aeo"] == 70.0
    assert report.five_pillar_scorecard["cro"] == 75.0
    assert report.five_pillar_scorecard["technical"] == 88.0

    # 9. Cross-discipline analysis
    assert "Technical crawling health" in report.cross_discipline_analysis

    # 10. Strategic priorities
    assert len(report.strategic_priorities) >= 4

    # 11. 30/60/90-day roadmap
    assert "30_day" in report.roadmap_30_60_90
    assert "60_day" in report.roadmap_30_60_90
    assert "90_day" in report.roadmap_30_60_90

    # 12. Data limitations
    assert len(report.data_limitations) >= 3


def test_phase11_2_specialist_reports_all_7_disciplines():
    """Verify that all 7 specialist reports follow the shared structural convention with unique diagnostic logic."""
    builder = SpecialistReportBuilder()

    findings = [
        {"finding_id": "F-01", "category": "SEO", "title": "Missing canonical tag"},
        {"finding_id": "F-02", "category": "GEO", "title": "Unbound Wikidata entity"},
        {"finding_id": "F-03", "category": "AEO", "title": "Excessive answer word count"},
        {"finding_id": "F-04", "category": "CRO", "title": "Excessive inquiry form fields"},
        {"finding_id": "F-05", "category": "COMPETITIVE", "title": "Competitor intent gap"},
        {"finding_id": "F-06", "category": "TECH_INFRASTRUCTURE", "title": "Render blocking script"},
        {"finding_id": "F-07", "category": "REMEDIATION_VERIFICATION", "title": "Unverified schema patch"},
    ]

    for disc in SpecialistDiscipline:
        sr: SpecialistReportData = builder.build_specialist_report(
            discipline=disc,
            domain="example.com",
            audit_id="aud_100",
            score=78.5,
            findings=findings,
        )

        assert sr.discipline == disc
        assert sr.domain == "example.com"
        assert sr.audit_id == "aud_100"

        # Shared structural conventions
        assert sr.metadata_header["discipline_name"] == disc.value
        assert sr.executive_diagnostic_summary
        assert len(sr.deep_dive_findings) >= 1
        assert len(sr.benchmark_comparative_tables) >= 1
        assert sr.technical_diagnostics
        assert len(sr.action_matrix) >= 2

        # Discipline-specific logic check
        if disc == SpecialistDiscipline.SEO:
            assert "canonical_status_distribution" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.GEO:
            assert "ai_crawler_access" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.AEO:
            assert "mean_answer_passage_word_count" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.CRO:
            assert "accessible_labels_present" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.COMPETITIVE:
            assert "benchmark_competitors_approved" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.TECH_INFRASTRUCTURE:
            assert "http_version" in sr.technical_diagnostics
        elif disc == SpecialistDiscipline.REMEDIATION_VERIFICATION:
            assert "open_remediation_tasks" in sr.technical_diagnostics


def test_phase11_3_finding_detail_pages_all_13_fields():
    """Verify that finding detail pages adhere strictly to the 13-field canonical contract."""
    builder = FindingDetailPageBuilder()

    finding = {
        "finding_id": "FIND-SEO-009",
        "category": "SEO",
        "title": "Missing Primary H1 Tag",
        "executive_explanation": "Pages lacking H1 tags dilute keyword relevance and search engine topical authority.",
        "technical_explanation": "HTML document body lacks a top-level <h1> node before secondary <h2> headings.",
        "affected_urls": ["https://example.com/products/a", "https://example.com/products/b"],
        "evidence_ids": ["ev_h1_001"],
        "root_cause": "Product detail template v2 omitted the {{ product.title }} heading tag.",
        "severity": "HIGH",
        "confidence": "VERIFIED",
        "impact": "Estimated 14% drop in organic search CTR.",
        "recommendation": "Inject single contextual <h1> matching product title.",
        "implementation_instructions": ["Open product.liquid", "Add <h1>{{ product.title }}</h1> inside .hero-wrap"],
        "acceptance_criteria": {"test_type": "DOM_CONDITION", "expected": "Exactly one non-empty <h1> exists."},
    }

    ledger = {
        "ev_h1_001": {
            "selector": "main.product-hero",
            "text": "<main class='product-hero'><!-- h1 omitted --></main>",
            "content_sha256": "abcdef1234567890",
            "fetched_at": "2026-11-19T00:00:00Z",
        }
    }

    remediation = {
        "business_impact": "Loss of keyword rankings across 2 primary product pages.",
        "root_cause": "Liquid template syntax error omitting <h1>.",
    }

    v_history = [
        {"run_id": "run_01", "status": "OPEN", "timestamp": "2026-11-10T12:00:00Z"}
    ]

    detail: FindingDetailPageData = builder.build_finding_detail(
        finding=finding,
        evidence_ledger=ledger,
        remediation_task=remediation,
        verification_history=v_history,
    )

    # 1. Finding identity
    assert detail.finding_id == "FIND-SEO-009"
    assert detail.category == "SEO"
    assert detail.title == "Missing Primary H1 Tag"

    # 2. Executive explanation
    assert "dilute keyword relevance" in detail.executive_explanation

    # 3. Technical explanation
    assert "lacks a top-level <h1> node" in detail.technical_explanation

    # 4. Affected URLs
    assert len(detail.affected_urls) == 2

    # 5. Evidence
    assert len(detail.evidence_tokens) == 1
    assert detail.evidence_tokens[0]["locator"] == "main.product-hero"
    assert detail.evidence_tokens[0]["hash"] == "abcdef1234567890"

    # 6. Root cause
    assert detail.root_cause

    # 7. Severity
    assert detail.severity == "HIGH"

    # 8. Confidence
    assert detail.confidence == "VERIFIED"

    # 9. Impact
    assert "14% drop" in detail.impact

    # 10. Recommendation
    assert "Inject single contextual <h1>" in detail.recommendation

    # 11. Implementation instructions
    assert len(detail.implementation_instructions) >= 2

    # 12. Acceptance criteria
    assert detail.acceptance_criteria["test_type"] == "DOM_CONDITION"

    # 13. Verification history
    assert len(detail.verification_history) == 1
    assert detail.verification_history[0]["status"] == "OPEN"


def test_phase11_4_interactive_evidence_explorer():
    """Verify that InteractiveEvidenceExplorer delivers drilldowns, before/after diffs, and workflow actions."""
    explorer = InteractiveEvidenceExplorer()

    # 1. Assembly of drilldown view
    view: EvidenceExplorerDTO = explorer.get_evidence_explorer_view(
        finding_id="F-001",
        affected_url="https://example.com/checkout",
        before_snippet="<form><input name='ssn'></form>",
        after_snippet="<form><input name='email'></form>",
    )
    assert view.finding_id == "F-001"
    assert view.affected_url == "https://example.com/checkout"
    assert view.screenshot_uri
    assert view.rendered_dom_snippet
    assert view.raw_evidence_hash
    assert view.before_after_diff["before"] == "<form><input name='ssn'></form>"
    assert view.code_patch_download_url.endswith("/F-001/download.diff")
    assert view.approval_status == "PENDING_APPROVAL"

    # 2. Assign remediation owner
    assign_event = explorer.assign_remediation("F-001", "lead-engineer@example.com")
    assert assign_event["owner"] == "lead-engineer@example.com"

    # 3. Approve changes
    approval_event = explorer.approve_change("F-001", "CHANGE_CODE_LOGIC", "sec-lead@example.com")
    assert approval_event["status"] == "APPROVED"
    assert approval_event["approver_tier"] == "CHANGE_CODE_LOGIC"

    # 4. Record verification outcome
    v_event = explorer.record_verification_outcome("F-001", "VERIFIED_FIXED", "Retest passed with zero errors.")
    assert v_event["status"] == "VERIFIED_FIXED"

    # 5. Check action audit trail
    history = explorer.get_action_history("F-001")
    assert len(history) == 3


def test_phase11_5_report_generation_engine():
    """Verify layout formatting, table pagination, chart validation, and PDF integrity testing."""
    config = ReportGenerationConfig(max_table_rows_per_page=3)
    gen = LayeredReportGenerationEngine(config)

    exec_b = ExecutiveReportBuilder()
    spec_b = SpecialistReportBuilder()
    find_b = FindingDetailPageBuilder()

    exec_rep = exec_b.build_report("example.com", "aud_doc_1")
    spec_reps = [spec_b.build_specialist_report(SpecialistDiscipline.SEO, "example.com", "aud_doc_1")]
    find_details = [find_b.build_finding_detail({"finding_id": "F-TOC-1", "severity": "HIGH", "title": "Sample Title"})]

    doc: GeneratedDocumentArtifact = gen.assemble_document(
        document_id="doc_aud_doc_1",
        title="Enterprise Audit Document",
        executive_report=exec_rep,
        specialist_reports=spec_reps,
        finding_details=find_details,
    )

    assert doc.document_id == "doc_aud_doc_1"
    assert doc.total_pages > 0
    assert len(doc.table_of_contents) >= 3
    assert doc.internal_references.get("F-TOC-1") is not None
    assert doc.charts_validated is True
    assert doc.pdf_integrity_certified is True
    assert len(doc.appendices) == 3

    # Table pagination chunking test
    rows = list(range(10))
    chunks = gen.paginate_table(rows)
    assert len(chunks) == 4  # [3, 3, 3, 1]
    assert len(chunks[0]) == 3
    assert len(chunks[-1]) == 1

    # Integrity tester rejection on placeholder text
    corrupted_html = doc.rendered_html + "<div>{{ unreplaced_var }}</div>"
    assert gen.test_pdf_integrity(corrupted_html, doc.total_pages, doc.table_of_contents) is False


def test_phase11_6_narrative_quality_engine_zero_metric_invention():
    """Verify narrative quality engine rejects fabricated numbers, contradictions, and duplicates."""
    engine = NarrativeQualityEngine(ttfb_slow_threshold_ms=800.0)

    audit_data = {
        "seo_score": 75.0,
        "geo_score": 70.0,
        "aeo_score": 65.0,
        "cro_score": 80.0,
        "tech_score": 85.0,
        "crawled_urls": 120,
        "broken_links_count": 4,
        "ttfb_ms": 1200.0,  # Slow TTFB > 800ms
    }

    # Step 1: Fact extraction
    facts = engine.extract_structured_facts(audit_data)
    assert len(facts) == 8
    assert facts["ttfb_ms"].metric_value == 1200.0

    # Step 6: Test rejection of hallucinated metrics
    hallucinated_narrative = (
        "The site had an SEO score of 75.0, but achieved an unrecorded 98.7% conversion lift "
        "and 4300 new monthly signups."
    )
    rejected = engine.independent_factual_critic(hallucinated_narrative, facts)
    assert len(rejected) >= 1
    assert any("98.7%" in r or "4300" in r for r in rejected)

    # Step 7: Test duplicate narrative detection
    sections = [
        "The site demonstrated strong crawling performance across all primary routes.",
        "The site demonstrated strong crawling performance across all primary routes.",  # duplicate
    ]
    dupes = engine.detect_duplicate_narratives(sections)
    assert len(dupes) == 1

    # Step 8: Test contradiction detection (claiming fast when TTFB is 1200ms)
    contradictory_text = "The server delivered blazing fast responses with instantaneous server response."
    contradictions = engine.check_contradictions(contradictory_text, facts)
    assert len(contradictions) >= 1
    assert "TTFB is 1200.0ms" in contradictions[0]

    # Step 10: Master verdict evaluation
    clean_narrative = (
        "The target domain demonstrated an SEO performance index of 75.0 "
        "and a GEO entity index of 70.0 across 120 crawled pages."
    )
    verdict_clean: NarrativeQualityVerdict = engine.validate_report_narrative(audit_data, clean_narrative)
    assert verdict_clean.critic_passed is True
    assert verdict_clean.final_validation_status == "APPROVED"

    verdict_bad: NarrativeQualityVerdict = engine.validate_report_narrative(audit_data, hallucinated_narrative)
    assert verdict_bad.critic_passed is False
    assert verdict_bad.final_validation_status == "REJECTED_BY_CRITIC"


def test_phase11_end_to_end_layered_report_workflow():
    """Verify end-to-end layered reporting orchestration assembling all tiers."""
    engine = LayeredReportingEngine()

    audit_data = {
        "seo_score": 84.0,
        "geo_score": 76.0,
        "aeo_score": 78.0,
        "cro_score": 82.0,
        "tech_score": 88.0,
        "crawled_urls": 50,
        "broken_links_count": 0,
        "ttfb_ms": 220.0,
    }

    findings = [
        {
            "finding_id": "FIND-01",
            "category": "SEO",
            "title": "Title Tag Length Sub-optimal",
            "severity": "MEDIUM",
            "confidence": "VERIFIED",
            "affected_urls": ["https://example.com/"],
        },
        {
            "finding_id": "FIND-02",
            "category": "GEO",
            "title": "Entity Disambiguation Required",
            "severity": "HIGH",
            "confidence": "VERIFIED",
            "affected_urls": ["https://example.com/about"],
        },
    ]

    bundle = engine.generate_layered_report_bundle(
        domain="example.com",
        audit_id="audit_e2e_11",
        audit_data=audit_data,
        findings=findings,
        client_name="Test Enterprise",
    )

    assert bundle["domain"] == "example.com"
    assert bundle["audit_id"] == "audit_e2e_11"

    # Narrative verdict
    assert bundle["narrative_verdict"].critic_passed is True

    # Executive report (12 sections)
    assert isinstance(bundle["executive_report"], ExecutiveReportData)
    assert bundle["executive_report"].five_pillar_scorecard["seo"] == 84.0

    # Specialist reports (7 disciplines)
    assert len(bundle["specialist_reports"]) == 7

    # Finding details (2 findings, 13 fields each)
    assert len(bundle["finding_details"]) == 2
    assert bundle["finding_details"][0].finding_id == "FIND-01"

    # Document artifact
    doc: GeneratedDocumentArtifact = bundle["document_artifact"]
    assert doc.pdf_integrity_certified is True
    assert doc.total_pages > 0
    assert len(doc.table_of_contents) >= 4
