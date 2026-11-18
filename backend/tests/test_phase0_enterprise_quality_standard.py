"""
Test Suite — Enterprise Quality Standard (Phase 0.1 to Phase 0.5)

Verifies:
1. Canonical Audit Data Model: 17 standardized entities with immutable identifiers.
2. Evidence Classification Engine: 8-state classification, SHA-256 integrity hashing, provenance tracking.
3. Finding Deduplication: Root cause aggregation collapsing isolated defects without issue count inflation.
4. Deterministic Scoring: Formula-driven metric evaluations, missing data rules, coverage-adjusted partial scoring.
5. Report Integrity Validation Gate: 10-point cross-surface gate blocking contradictory or unbacked reports.
"""
import pytest
from datetime import datetime, timezone
import json

from app.domain.enums import (
    EvidenceStatus,
    MetricDirection,
    MissingDataRule,
    RootCauseTaxonomy,
    Severity,
    Category,
    FindingStatus,
    PublicationStatus,
)
from app.domain.canonical_audit_model import (
    CanonicalAuditRun,
    DomainProfile,
    CanonicalBusinessProfile,
    CrawlInventory,
    CrawlPage,
    PageSnapshot,
    EvidenceRecord,
    CanonicalFinding,
    MetricResult,
    ScoreResult,
    CanonicalRecommendation,
    RemediationTask,
    VerificationRun,
    CompetitorProfile,
    BenchmarkResult,
    ReportArtifact,
    AuditEvent,
)
from app.domain.evidence.classification_engine import EvidenceClassificationEngine
from app.orchestration.finding_deduplicator import RootCauseRegistry, FindingDeduplicator
from app.domain.scoring.deterministic_calculator import (
    DeterministicMetricCalculator,
    DeterministicScoreEngine,
)
from app.reports.validation_gate import ReportPublicationValidator
from app.domain.models import ExecutiveReport, OverallScoreResult, Finding, FindingEvidence, CategoryScore


def test_phase0_1_canonical_audit_data_model_suite():
    """Verify all 17 core entities can be instantiated with unified execution identifiers."""
    run_id = "RUN_ENT_001"
    domain_id = "example.com"

    # 1. AuditRun
    run = CanonicalAuditRun(
        id=run_id,
        audit_run_id=run_id,
        domain_id=domain_id,
        domain="example.com",
        publication_status=PublicationStatus.INTERNAL_REVIEW,
    )
    assert run.audit_run_id == run_id

    # 2. DomainProfile
    dp = DomainProfile(
        audit_run_id=run_id,
        domain_id=domain_id,
        domain="example.com",
        primary_hostname="www.example.com",
        brand_name="Example",
        root_url="https://example.com",
    )
    assert dp.brand_name == "Example"

    # 3. BusinessProfile
    bp = CanonicalBusinessProfile(
        audit_run_id=run_id,
        domain_id=domain_id,
        business_name="Example Corp",
        business_model="B2B",
    )
    assert bp.business_model == "B2B"

    # 4. CrawlInventory
    inv = CrawlInventory(
        audit_run_id=run_id,
        domain_id=domain_id,
        inventory_id="inv_001",
        discovered_urls_count=500,
        inspected_urls_count=25,
        coverage_ratio=0.05,
    )
    assert inv.inspected_urls_count == 25

    # 5. CrawlPage
    page = CrawlPage(
        audit_run_id=run_id,
        domain_id=domain_id,
        page_id="pg_001",
        url="https://example.com/about",
        ttfb_ms=245.0,
    )
    assert page.ttfb_ms == 245.0

    # 6. PageSnapshot
    snap = PageSnapshot(
        audit_run_id=run_id,
        domain_id=domain_id,
        snapshot_id="snp_001",
        page_id="pg_001",
        url="https://example.com/about",
        raw_html_sha256="abc123hash",
    )
    assert snap.raw_html_sha256 == "abc123hash"

    # 7. EvidenceRecord
    ev = EvidenceRecord(
        audit_run_id=run_id,
        domain_id=domain_id,
        evidence_id="ev_001",
        classification=EvidenceStatus.MEASURED,
        collection_method="HTTP_GET",
        source_system="PROBER",
        raw_value=245.0,
        content_hash="deadbeef",
    )
    assert ev.raw_value == 245.0

    # 8. CanonicalFinding
    fnd = CanonicalFinding(
        audit_run_id=run_id,
        domain_id=domain_id,
        finding_id="FND_001",
        root_cause_key=RootCauseTaxonomy.UNOPTIMIZED_TTFB,
        title="High TTFB",
        description="Observed high TTFB on 1 page.",
        severity=Severity.HIGH,
    )
    assert fnd.root_cause_key == RootCauseTaxonomy.UNOPTIMIZED_TTFB

    # 9. MetricResult
    mr = MetricResult(
        audit_run_id=run_id,
        domain_id=domain_id,
        metric_id="PERF_TTFB",
        raw_value=245.0,
        normalized_score=95.0,
    )
    assert mr.normalized_score == 95.0

    # 10. ScoreResult
    sr = ScoreResult(
        audit_run_id=run_id,
        domain_id=domain_id,
        score_id="scr_001",
        overall_score=85.0,
        grade="B",
    )
    assert sr.grade == "B"

    # 11. Recommendation
    rec = CanonicalRecommendation(
        audit_run_id=run_id,
        domain_id=domain_id,
        recommendation_id="rec_001",
        finding_id="FND_001",
        title="Enable Cloudflare Edge Caching",
    )
    assert rec.recommendation_id == "rec_001"

    # 12. RemediationTask
    task = RemediationTask(
        audit_run_id=run_id,
        domain_id=domain_id,
        task_id="tsk_001",
        recommendation_id="rec_001",
        finding_id="FND_001",
        status="IN_PROGRESS",
    )
    assert task.status == "IN_PROGRESS"

    # 13. VerificationRun
    vr = VerificationRun(
        audit_run_id=run_id,
        domain_id=domain_id,
        verification_id="ver_001",
        task_id="tsk_001",
        finding_id="FND_001",
        is_verified_fixed=True,
    )
    assert vr.is_verified_fixed is True

    # 14. CompetitorProfile
    comp = CompetitorProfile(
        audit_run_id=run_id,
        domain_id=domain_id,
        competitor_id="comp_001",
        domain="competitor.com",
        company_name="Competitor Inc",
    )
    assert comp.domain == "competitor.com"

    # 15. BenchmarkResult
    bm = BenchmarkResult(
        audit_run_id=run_id,
        domain_id=domain_id,
        benchmark_id="bm_001",
        metric_id="PERF_TTFB",
        industry="Dental eCommerce",
        median_value=320.0,
        top_quartile_value=220.0,
    )
    assert bm.median_value == 320.0

    # 16. ReportArtifact
    art = ReportArtifact(
        audit_run_id=run_id,
        domain_id=domain_id,
        artifact_id="art_001",
        report_type="MASTER_BOOK",
        sha256_checksum="sha256artifact",
    )
    assert art.report_type == "MASTER_BOOK"

    # 17. AuditEvent
    event = AuditEvent(
        audit_run_id=run_id,
        domain_id=domain_id,
        event_id="evt_001",
        event_type="CRAWL_COMPLETED",
    )
    assert event.event_type == "CRAWL_COMPLETED"


def test_phase0_2_evidence_classification_and_provenance():
    """Verify EvidenceClassificationEngine captures metadata, SHA-256 hash, and provenance."""
    raw_dom = {"tag": "img", "src": "/logo.png", "alt": ""}
    record = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id="RUN_CLASSIFY_01",
        domain_id="perforacare.com",
        classification=EvidenceStatus.OBSERVED,
        source_system="HTML_PARSER",
        collection_method="DOM_QUERY",
        raw_value=raw_dom,
        expected_condition="Descriptive alt attribute",
        observed_condition="Empty alt attribute: alt=''",
        confidence_rationale="Deterministic AST tag inspection.",
        url="https://perforacare.com/",
    )

    assert record.classification == EvidenceStatus.OBSERVED
    assert len(record.content_hash) == 64  # Valid SHA-256 hex string
    assert record.provenance_details["source_system"] == "HTML_PARSER"
    assert record.provenance_details["provenance_verified"] is True

    # Test integrity check
    valid, msg = EvidenceClassificationEngine.verify_record_integrity(record)
    assert valid is True

    # Tamper with raw_value to verify integrity detector detects modification
    record.raw_value["alt"] = "Tampered alt text"
    tampered_valid, tampered_msg = EvidenceClassificationEngine.verify_record_integrity(record)
    assert tampered_valid is False
    assert "Integrity violation" in tampered_msg


def test_phase0_3_root_cause_finding_deduplication():
    """Verify that multiple element defects collapse into one canonical finding with element evidence."""
    run_id = "RUN_DEDUP_01"
    domain_id = "perforacare.com"

    # 4 distinct missing alt image observations across 3 pages
    ev1 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.OBSERVED,
        source_system="DOM",
        collection_method="NON_TEXT_CONTENT",
        raw_value={"img": "hero.jpg"},
        observed_condition="Missing image alt text",
        url="https://perforacare.com/",
    )
    ev2 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.OBSERVED,
        source_system="DOM",
        collection_method="NON_TEXT_CONTENT",
        raw_value={"img": "prod1.jpg"},
        observed_condition="Missing image alt text",
        url="https://perforacare.com/product-a",
    )
    ev3 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.OBSERVED,
        source_system="DOM",
        collection_method="NON_TEXT_CONTENT",
        raw_value={"img": "prod2.jpg"},
        observed_condition="Missing image alt text",
        url="https://perforacare.com/product-a",
    )
    ev4 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.OBSERVED,
        source_system="DOM",
        collection_method="NON_TEXT_CONTENT",
        raw_value={"img": "banner.jpg"},
        observed_condition="Missing image alt text",
        url="https://perforacare.com/product-b",
    )

    findings = FindingDeduplicator.aggregate_evidence_into_canonical_findings(
        audit_run_id=run_id,
        domain_id=domain_id,
        evidence_records=[ev1, ev2, ev3, ev4],
    )

    # Exactly 1 canonical finding must be generated (not 4 duplicate findings!)
    assert len(findings) == 1
    canonical_fnd = findings[0]
    assert canonical_fnd.root_cause_key == RootCauseTaxonomy.MISSING_ALT_TEXT
    assert "4 inspected image element(s)" in canonical_fnd.title
    assert len(canonical_fnd.affected_urls) == 3
    assert len(canonical_fnd.evidence_ids) == 4
    assert len(canonical_fnd.evidence_records) == 4
    # Multiple disciplines cross-referenced
    assert "TECHNICAL_SEO" in canonical_fnd.relevant_disciplines
    assert "ACCESSIBILITY" in canonical_fnd.relevant_disciplines


def test_phase0_4_deterministic_scoring_and_unmeasured_integrity():
    """Verify deterministic scoring eliminates silent zero penalties and supports partial assessments."""
    run_id = "RUN_SCORE_01"
    domain_id = "example.com"

    ev1 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.MEASURED,
        source_system="PROBER",
        collection_method="TTFB",
        raw_value=250.0,
    )
    ev2 = EvidenceClassificationEngine.create_evidence_record(
        audit_run_id=run_id,
        domain_id=domain_id,
        classification=EvidenceStatus.MEASURED,
        source_system="PROBER",
        collection_method="TTFB",
        raw_value=350.0,
    )

    # 1. Measured metric (TTFB: lower is better, benchmark 400ms)
    metric_ttfb = DeterministicMetricCalculator.evaluate_metric(
        audit_run_id=run_id,
        domain_id=domain_id,
        metric_id="PERF_TTFB",
        name="Server Response Time",
        formula_version="1.0",
        direction=MetricDirection.LOWER_IS_BETTER,
        benchmark_value=400.0,
        weight=20.0,
        missing_data_rule=MissingDataRule.UNMEASURED_FLAG,
        evidence_records=[ev1, ev2],
    )
    assert metric_ttfb.classification == EvidenceStatus.MEASURED
    assert metric_ttfb.raw_value == 300.0  # (250 + 350) / 2
    assert metric_ttfb.normalized_score == 100.0  # <= benchmark

    # 2. Unmeasured metric (GA4 / GSC unconfigured: MUST NOT SILENTLY BE ZERO!)
    metric_unmeasured = DeterministicMetricCalculator.evaluate_metric(
        audit_run_id=run_id,
        domain_id=domain_id,
        metric_id="ANALYTICS_BOUNCE",
        name="Visitor Engagement",
        formula_version="1.0",
        direction=MetricDirection.HIGHER_IS_BETTER,
        benchmark_value=60.0,
        weight=20.0,
        missing_data_rule=MissingDataRule.UNMEASURED_FLAG,
        evidence_records=[],  # No evidence
    )
    assert metric_unmeasured.classification == EvidenceStatus.UNAVAILABLE
    assert metric_unmeasured.normalized_score is None  # Never silently 0.0!
    assert metric_unmeasured.confidence == 0.0

    # 3. Composite score assembly with partial coverage
    score_result = DeterministicScoreEngine.assemble_composite_score(
        audit_run_id=run_id,
        domain_id=domain_id,
        metric_results=[metric_ttfb, metric_unmeasured],
        category_weights={"PERF": 50.0, "ANALYTICS": 50.0},
    )
    assert score_result.is_partial_assessment is True
    assert score_result.coverage_score == 0.50
    assert any("PARTIAL ASSESSMENT" in trail for trail in score_result.formula_audit_trail)


def test_phase0_5_report_integrity_validation_gate():
    """Verify ReportPublicationValidator halts publication when cross-surface contradictions exist."""
    base_scores = OverallScoreResult(
        overall_score=80.0,
        grade="B",
        health_label="Good",
        category_scores={
            "SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=80.0, grade="B", health_label="Good"),
            "PERF": CategoryScore(category=Category.TECHNICAL_SEO, score=80.0, grade="B", health_label="Good"),
        }
    )

    report = ExecutiveReport(
        org_id="test_org",
        report_id="RUN_PUB_001",
        analysis_id="RUN_PUB_001",
        audit_id="RUN_PUB_001",
        domain="example.com",
        website_url="https://example.com",
        generated_at="2026-10-15T12:00:00Z",
        scores=base_scores,
        story_summary="Test publication story.",
        primary_strategic_opportunity="Opportunity.",
        consultant_advice_what_to_ignore="Ignore.",
        findings=[
            Finding(
                finding_id="FND_001",
                category=Category.TECHNICAL_SEO,
                title="Missing Canonical",
                severity=Severity.HIGH,
                impact=8,
                evidence=[FindingEvidence(url="https://example.com", selector="head", text="canonical")],
            )
        ],
        crawl_manifest={"total_pages_discovered": 10, "pages": [{"url": f"https://example.com/{i}"} for i in range(10)]},
        certification_status="NOT_ASSESSED",
    )

    # 1. Clean report passes
    res_clean = ReportPublicationValidator.validate_publication_bundle(report)
    assert res_clean.is_publishable is True

    # 2. Contradiction: Inspected count > Discovered count
    report_bad_crawl = report.model_copy(deep=True)
    report_bad_crawl.crawl_manifest = {
        "total_pages_discovered": 5,
        "pages": [{"url": f"https://example.com/{i}"} for i in range(12)], # 12 > 5!
    }
    res_bad_crawl = ReportPublicationValidator.validate_publication_bundle(report_bad_crawl)
    assert res_bad_crawl.is_publishable is False
    assert any("Crawl inventory contradiction" in r for r in res_bad_crawl.blocking_reasons)

    # 3. Contradiction: Certified status claimed while essential categories are unmeasured
    report_false_cert = report.model_copy(deep=True)
    report_false_cert.certification_status = "CERTIFIED"
    report_false_cert.scores.category_scores["AEO"] = CategoryScore(
        category=Category.AI_SEARCH,
        score=None,
        health_label="NOT MEASURED",
    )
    res_false_cert = ReportPublicationValidator.validate_publication_bundle(report_false_cert)
    assert res_false_cert.is_publishable is False
    assert any("essential categories are unmeasured" in r for r in res_false_cert.blocking_reasons)
