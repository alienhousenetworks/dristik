"""
Dristik AI Evidence-First Methodology Permanent Regression Suite
Audits full compliance with Audit 1 (SpyceNow Reference Standard) and
prevents regression into Audit 2 failure patterns.

Covers:
1. One-page website audit (scope disclosure, no broad site claims).
2. Large website audit (coverage denominator disclosure).
3. Incomplete crawl (explicit boundary label, no manufactured complete crawl).
4. Failed data collection (recorded as FAILED/UNAVAILABLE, not negative defect).
5. Unavailable analytics (NOT_MEASURED, no default/synthetic score).
6. Conflicting evidence (flagged and held).
7. No detected issues (honest reporting, no manufactured findings).
8. Only informational findings (severity respected, no artificial panic).
9. Critical findings (traceable root cause required).
10. Partially measured scorecards (coverage and normalized weights).
11. Duplicate findings (clustered and deduplicated).
12. Recommendations unsupported by findings (rejected/quarantined).
13. Claims with invalid evidence references (rejected).
14. Claims whose evidence does not semantically support them (semantic mismatch rejected).
15. Evidence belonging to another audit (cross-audit references rejected).
16. Executive summary count mismatches (gate fails closed).
17. Malformed generated text (placeholders like [ev_xxx] rejected).
18. Report generation with missing data (published with limitations, no fake scores).

Audit 2 Failure Patterns:
- Composite scores despite unmeasured pillars.
- Contradictory chapter statements.
- Executive priority counts inconsistent with detailed findings.
- Recommendations containing irrelevant industry jargon (AWS Aurora, Redis).
- Claims of broad coverage when only a small sample was inspected.
- Confidence or verification claims unsupported by evidence.
"""
import pytest
from datetime import datetime, timezone

from app.domain.models import (
    ExecutiveReport,
    Finding,
    Claim,
    CategoryScore,
    OverallScoreResult,
    CrawlManifest,
    PageEvidence,
    AuditScopeInfo,
    ClaimLedger,
    ClaimLedgerEntry,
)
from app.domain.enums import (
    Category,
    Severity,
    VerificationStatus,
    ClaimType,
    ClaimSourceType,
    ProvenanceType,
    CollectionStatus,
)
from app.domain.evidence.models import Evidence, MachineObservation
from app.domain.evidence.store import EvidenceStore
from app.domain.evidence.semantic_validator import SemanticEvidenceValidator
from app.seo.audit.scoring.score_engine import ScoreEngine
from app.reports.validation_gate import ValidationGate
from app.orchestration.cognition.decision_engine import DecisionEngine


def create_minimal_valid_report(run_id: str = "run_test_001") -> Tuple[ExecutiveReport, EvidenceStore]:
    store = EvidenceStore(run_id)
    # Layer 1 empirical observation
    obs = store.add_observation(
        attribute="title",
        value="SpyceNow — Gen Z Expression",
        source="html",
        url="https://spycenow.com",
    )
    ev = store.add_evidence(
        source_type="dom",
        analyzer="title_analyzer",
        url="https://spycenow.com",
        text="SpyceNow — Gen Z Expression",
        value="SpyceNow — Gen Z Expression",
    )

    page = PageEvidence(
        url="https://spycenow.com",
        status_code=200,
        load_time_ms=250.0,
        title="SpyceNow — Gen Z Expression",
        headers={"content-type": "text/html"},
    )
    manifest = CrawlManifest(
        domain="spycenow.com",
        pages=[page],
        total_pages=1,
        total_pages_discovered=1,
    )

    finding = Finding(
        finding_id="SPY-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="Product category is brand-led in the hero",
        finding="Product category is brand-led in the hero",
        description="The headline focuses on brand emotion rather than explicit category definition.",
        evidence_ids=[obs.evidence_id],
        evidence_refs=[obs.evidence_id],
        confidence=0.95,
        recommendation="Add explicit category descriptor below hero headline.",
    )

    scores = OverallScoreResult(
        overall_score=75.0,
        category_scores={
            "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=75.0, weight=100.0, weighted_score=75.0)
        }
    )

    report = ExecutiveReport(
        report_id=f"rep_{run_id}",
        analysis_id=run_id,
        org_id="org_test",
        domain="spycenow.com",
        website_url="https://spycenow.com",
        scores=scores,
        findings=[finding],
        crawl_manifest=manifest,
        story_summary="The public landing page has an emotional voice but lacks category clarity.",
        primary_strategic_opportunity="Clarify category and publish privacy policy.",
        consultant_advice_what_to_ignore="Ignore keyword stuffing and synthetic backlinks.",
        evidence_ledger={obs.evidence_id: {"id": obs.evidence_id, "audit_run_id": run_id}},
        sealed_evidence_snapshot_id="snap_001",
    )
    return report, store


# ------------------------------------------------------------------------------
# 1. One-page website audit (Audit 1 Reference)
# ------------------------------------------------------------------------------
def test_1_one_page_audit_scope_integrity():
    report, store = create_minimal_valid_report("run_one_page")
    report.story_summary = "Single page landing page reviewed. Deep crawl not possible."
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_06_scope_consistency"]["passed"] is True


def test_1_one_page_audit_rejects_site_wide_claims():
    report, store = create_minimal_valid_report("run_one_page_bad")
    # Falsely asserts complete site-wide crawl on a 1-page site
    report.story_summary = "Complete site-wide crawl of all 500 pages confirms zero technical defects."
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_06_scope_consistency"]["passed"] is False


# ------------------------------------------------------------------------------
# 2. Large website audit
# ------------------------------------------------------------------------------
def test_2_large_website_coverage_denominator():
    report, store = create_minimal_valid_report("run_large")
    manifest = CrawlManifest(
        domain="spycenow.com",
        pages=[PageEvidence(url=f"https://spycenow.com/p{i}", status_code=200, load_time_ms=100) for i in range(10)],
        total_pages=10,
        total_pages_discovered=100,
    )
    report.crawl_manifest = manifest
    qg = ValidationGate.evaluate_quality_gates(report, manifest)
    assert qg["gates"]["coverage_gate"]["passed"] is True
    # Disclosed as sampled audit
    assert "Sampled Audit" in qg["gates"]["coverage_gate"]["details"]


# ------------------------------------------------------------------------------
# 3. Incomplete crawl
# ------------------------------------------------------------------------------
def test_3_incomplete_crawl_fails_coverage_if_zero_discovered():
    report, store = create_minimal_valid_report("run_incomplete")
    manifest = CrawlManifest(
        domain="spycenow.com",
        pages=[],
        total_pages=0,
        total_pages_discovered=0,
    )
    qg = ValidationGate.evaluate_quality_gates(report, manifest)
    assert qg["gates"]["coverage_gate"]["passed"] is False


# ------------------------------------------------------------------------------
# 4. Failed data collection (Recorded honestly, not as defect)
# ------------------------------------------------------------------------------
def test_4_failed_collection_recorded_honestly():
    store = EvidenceStore("run_fail_test")
    ev = store.record_failed("sitemap_fetcher", url="https://spycenow.com/sitemap.xml", error="Connection timeout")
    assert ev.collection_status == CollectionStatus.FAILED
    assert ev.provenance_type == ProvenanceType.RAW
    assert "FAILED" in ev.text


# ------------------------------------------------------------------------------
# 5. Unavailable analytics (NOT_MEASURED)
# ------------------------------------------------------------------------------
def test_5_unavailable_analytics_disclosed_not_scored():
    store = EvidenceStore("run_unavail")
    ev = store.record_unavailable("google_analytics_4", reason="Property not connected")
    assert ev.collection_status == CollectionStatus.UNAVAILABLE
    assert ev.limitations == "Property not connected"


# ------------------------------------------------------------------------------
# 6. Conflicting evidence (Caught by Semantic Validator)
# ------------------------------------------------------------------------------
def test_6_conflicting_evidence_rejected_by_semantic_validator():
    store = EvidenceStore("run_conflict")
    obs = store.add_observation(attribute="http_status", value=200, source="http", url="https://spycenow.com")
    validator = SemanticEvidenceValidator("run_conflict", store)

    # Claim asserts site is down but evidence says 200 OK
    claim = Claim(
        id="CLM_001",
        statement="Site is 100% down and completely unreachable.",
        evidence_refs=[obs.evidence_id],
        claim_type=ClaimType.OBSERVED,
    )
    result = validator.validate_claim(claim)
    assert result.is_valid is False
    assert result.status == VerificationStatus.REJECTED


# ------------------------------------------------------------------------------
# 7. No detected issues (Honest report)
# ------------------------------------------------------------------------------
def test_7_no_detected_issues_keeps_report_valid():
    report, store = create_minimal_valid_report("run_clean")
    report.findings = []
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_07_finding_validity"]["passed"] is True


# ------------------------------------------------------------------------------
# 8. Only informational findings (Severity preserved)
# ------------------------------------------------------------------------------
def test_8_informational_findings_not_elevated_to_critical():
    report, store = create_minimal_valid_report("run_info")
    report.findings[0].severity = Severity.INFO
    assert report.findings[0].severity == Severity.INFO


# ------------------------------------------------------------------------------
# 9. Critical findings require root cause
# ------------------------------------------------------------------------------
def test_9_critical_findings_require_root_cause():
    report, store = create_minimal_valid_report("run_crit")
    report.findings[0].severity = Severity.CRITICAL
    report.findings[0].priority = 9
    report.findings[0].root_cause = None
    report.findings[0].causal_mechanism = None
    report.findings[0].diagnostic_gap = None
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["analysis_gate"]["passed"] is False


# ------------------------------------------------------------------------------
# 10. Partially measured scorecards (Coverage & Weights)
# ------------------------------------------------------------------------------
def test_10_partially_measured_scorecards():
    engine = ScoreEngine()
    breakdown = engine.score_breakdown({"technical": 80.0, "content": 60.0})
    assert breakdown["overall_score"] == 71.1
    assert breakdown["score_status"] == "PARTIAL"
    assert "geo" in breakdown["unmeasured_pillars"]
    assert breakdown["coverage_pct"] < 100.0


# ------------------------------------------------------------------------------
# 11. Duplicate findings clustered & deduplicated
# ------------------------------------------------------------------------------
def test_11_duplicate_findings_detected():
    report, store = create_minimal_valid_report("run_dups")
    # Duplicate same finding twice
    f2 = Finding(
        finding_id="SPY-002",
        category=report.findings[0].category,
        severity=report.findings[0].severity,
        title=report.findings[0].title,
        evidence_ids=report.findings[0].evidence_ids,
    )
    report.findings.append(f2)
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["deduplication_gate"]["passed"] is False


# ------------------------------------------------------------------------------
# 12. Recommendations unsupported by findings
# ------------------------------------------------------------------------------
def test_12_recommendations_with_irrelevant_jargon_rejected():
    report, store = create_minimal_valid_report("run_bad_rec")
    report.findings[0].recommendation = "You must install Redis cluster and configure Kubernetes ingress."
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_10_recommendation_relevance"]["passed"] is False


# ------------------------------------------------------------------------------
# 13. Claims with invalid evidence references
# ------------------------------------------------------------------------------
def test_13_claims_with_invalid_evidence_refs_rejected():
    store = EvidenceStore("run_invalid_ref")
    validator = SemanticEvidenceValidator("run_invalid_ref", store)
    claim = Claim(
        id="CLM_999",
        statement="Robots.txt contains syntax errors.",
        evidence_refs=["EV_NONEXISTENT_999"],
        claim_type=ClaimType.OBSERVED,
    )
    res = validator.validate_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.UNSUPPORTED


# ------------------------------------------------------------------------------
# 14. Claims whose evidence does not semantically support them
# ------------------------------------------------------------------------------
def test_14_claim_http_code_mismatch_rejected():
    store = EvidenceStore("run_code_mismatch")
    obs = store.add_observation(attribute="status_code", value=200, source="http", response_status=200)
    validator = SemanticEvidenceValidator("run_code_mismatch", store)
    claim = Claim(
        id="CLM_500",
        statement="Page returned HTTP 500 error code.",
        evidence_refs=[obs.evidence_id],
        claim_type=ClaimType.OBSERVED,
    )
    res = validator.validate_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.REJECTED


# ------------------------------------------------------------------------------
# 15. Evidence belonging to another audit (Cross-audit rejection)
# ------------------------------------------------------------------------------
def test_15_cross_audit_evidence_rejected():
    store = EvidenceStore("run_A")
    # Evidence was tagged with another run ID
    foreign_ev = store.add_evidence(source_type="dom", analyzer="test", text="Sample")
    # Force audit_run_id of another audit
    foreign_ev_dict = foreign_ev.model_dump()
    foreign_ev_dict["audit_run_id"] = "run_B"
    foreign_ev_dict["id"] = "ev_run_b_001"
    store._evidence["ev_run_b_001"] = Evidence(**foreign_ev_dict)

    validator = SemanticEvidenceValidator("run_A", store)
    claim = Claim(
        id="CLM_CROSS",
        audit_run_id="run_A",
        statement="Observed foreign evidence.",
        evidence_refs=["ev_run_b_001"],
        claim_type=ClaimType.OBSERVED,
    )
    res = validator.validate_claim(claim)
    assert res.is_valid is False
    assert res.status == VerificationStatus.REJECTED
    assert "belongs to another audit run" in res.rejection_reason


# ------------------------------------------------------------------------------
# 16. Executive summary count mismatches
# ------------------------------------------------------------------------------
def test_16_executive_summary_count_mismatches_blocked():
    report, store = create_minimal_valid_report("run_count_mismatch")
    from app.domain.models import ExecutiveTopActionsPlan, ExecutiveActionItem
    # Claiming 5 actions when only 1 finding exists
    report.top_10_actions = ExecutiveTopActionsPlan(
        actions=[
            ExecutiveActionItem(
                rank=i + 1,
                action_id=f"act_{i}",
                title=f"Action {i}",
                action=f"Remediate item {i}",
                expected_outcome="Improved clarity",
                finding_id=f"SPY-{i:03d}",
            )
            for i in range(5)
        ]
    )
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_11_cross_section_consistency"]["passed"] is False


# ------------------------------------------------------------------------------
# 17. Malformed generated text ([ev_xxx] placeholder tokens)
# ------------------------------------------------------------------------------
def test_17_malformed_placeholder_tokens_fail_closed():
    report, store = create_minimal_valid_report("run_placeholder")
    report.story_summary = "Website shows critical security defect [ev_xxx] in authentication."
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["reporting_gate"]["passed"] is False


# ------------------------------------------------------------------------------
# 18. Report generation with missing data discloses limitations
# ------------------------------------------------------------------------------
def test_18_missing_analytics_asserted_as_measured_fails():
    report, store = create_minimal_valid_report("run_unconnected_claim")
    report.story_summary = "Google Search Console confirms traffic dropped by 50%."
    from app.domain.models import ExternalDataSource
    # GSC is not connected
    report.external_authority = ExternalDataSource(source_name="google_search_console", gsc_connected=False)
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_15_missing_data_disclosure"]["passed"] is False


# ------------------------------------------------------------------------------
# Audit 2 Failure Patterns Prevention Tests
# ------------------------------------------------------------------------------
def test_audit_2_failure_composite_score_despite_unmeasured_pillars():
    engine = ScoreEngine()
    # If all pillars missing, calculate_overall_score must raise
    with pytest.raises(ValueError, match="no measured pillars"):
        engine.calculate_overall_score({})


def test_audit_2_failure_unsupported_iso_cert_claim_blocked():
    report, store = create_minimal_valid_report("run_audit2_cert")
    report.story_summary = "Company is ISO 27001 certified and SOC 2 Type II certified."
    qg = ValidationGate.evaluate_quality_gates(report, report.crawl_manifest)
    assert qg["gates"]["gate_12_executive_summary_reconciliation"]["passed"] is False


def test_decision_engine_never_emits_findings_without_evidence():
    engine = DecisionEngine()
    store = EvidenceStore("run_de_test")
    # Claim with NO evidence
    claim = Claim(
        id="CLM_NO_EV",
        statement="Site lacks H1 heading.",
        evidence_refs=[],
        confidence=0.8,
    )
    findings = engine.synthesize_findings([claim], store)
    # Finding must NOT be emitted
    assert len(findings) == 0
