"""
Comprehensive Test Suite for Phase 5 (100-Point Mathematical Scoring)
and Phase 6 (Post-Audit SEO Remediation Intelligence).
"""
from __future__ import annotations

import pytest

from app.seo.audit.scoring.mathematical_score_engine import (
    ConfidenceBreakdown,
    DimensionResult,
    MathematicalScoreEngine,
    MetricCheck,
    ScoreInterpretation,
    interpret_score,
)
from app.seo.audit.remediation.post_audit_remediation_engine import (
    FixType,
    PlatformType,
    PostAuditRemediationEngine,
    RemediationTask,
)
from app.seo.audit.orchestrator import SEOAuditOrchestrator
from app.seo.audit.orchestration.execution_state import AuditConfiguration, AuditMode


def test_score_interpretation_bands():
    assert interpret_score(95.0) == ScoreInterpretation.EXCELLENT
    assert interpret_score(85.0) == ScoreInterpretation.STRONG
    assert interpret_score(75.0) == ScoreInterpretation.GOOD
    assert interpret_score(65.0) == ScoreInterpretation.NEEDS_IMPROVEMENT
    assert interpret_score(45.0) == ScoreInterpretation.WEAK
    assert interpret_score(25.0) == ScoreInterpretation.CRITICAL
    assert interpret_score(None) == ScoreInterpretation.UNMEASURED


def test_metric_score_calculation():
    engine = MathematicalScoreEngine()
    checks = [
        MetricCheck(check_id="c1", weight=2.0, passed=True),
        MetricCheck(check_id="c2", weight=1.0, passed=False),
        MetricCheck(check_id="c3", weight=1.0, passed=True),
    ]
    # Total executed weight = 4.0, Passed weight = 3.0 -> S_i = 100 * (3 / 4) = 75.0%
    score = engine.calculate_metric_score(checks)
    assert score == 75.0


def test_conditional_applicability_exclusion():
    """Verifies that an inapplicable dimension is excluded from the denominator without penalty."""
    engine = MathematicalScoreEngine()
    dim_results = []

    for dim_id, cfg in engine.DIMENSION_WEIGHTS.items():
        if dim_id == "specialist_applicability":
            # Target is a SaaS site: local/ecommerce is inapplicable
            res = engine.calculate_dimension_score(dim_id, [], is_applicable=False)
        else:
            checks = [
                MetricCheck(check_id=f"chk_{dim_id}_1", weight=1.0, passed=True),
                MetricCheck(check_id=f"chk_{dim_id}_2", weight=1.0, passed=True),
            ]
            res = engine.calculate_dimension_score(dim_id, checks, is_applicable=True)
        dim_results.append(res)

    scorecard = engine.calculate_scorecard(dim_results)
    # Total applicable weight was 0.95 (1.0 - 0.05). All measured checks passed (100.0).
    assert scorecard.overall_health_score == 100.0
    assert scorecard.active_weight_sum == 0.95
    assert scorecard.excluded_dimensions_count == 1
    assert any("excluded from denominator without penalty" in d for d in scorecard.disclosures)


def test_unmeasured_dimension_exclusion():
    """Verifies that missing connector data (e.g. Backlinks) is not treated as 0."""
    engine = MathematicalScoreEngine()
    dim_results = []

    for dim_id, cfg in engine.DIMENSION_WEIGHTS.items():
        if dim_id == "trust_authority_signals":
            # Backlink connector disconnected: applicable but unmeasured
            res = engine.calculate_dimension_score(dim_id, [], is_applicable=True)
        else:
            checks = [MetricCheck(check_id=f"chk_{dim_id}", weight=1.0, passed=True)]
            res = engine.calculate_dimension_score(dim_id, checks, is_applicable=True)
        dim_results.append(res)

    scorecard = engine.calculate_scorecard(dim_results)
    # Authority was 0.05. Active weight = 0.95. Score must remain 100.0, NOT 95.0.
    assert scorecard.overall_health_score == 100.0
    assert scorecard.measured_dimensions_count == 8
    assert scorecard.excluded_dimensions_count == 1


def test_independent_confidence_vectors():
    """Verifies that SEO Health and Audit Coverage are tracked independently."""
    engine = MathematicalScoreEngine()
    checks = [MetricCheck(check_id="c1", weight=1.0, passed=True)]
    dim = engine.calculate_dimension_score("technical_crawlability", checks)

    confidence = ConfidenceBreakdown(
        audit_coverage_pct=12.5,
        evidence_confidence_pct=98.0,
        data_freshness_hours=0.5,
        connector_completeness_pct=60.0,
        sampling_status="SAMPLED_AUDIT",
    )
    scorecard = engine.calculate_scorecard([dim], confidence)

    # Health is 100.0, but coverage is clearly 12.5%
    assert scorecard.overall_health_score == 100.0
    assert scorecard.confidence_vectors.audit_coverage_pct == 12.5
    assert scorecard.confidence_vectors.sampling_status == "SAMPLED_AUDIT"


def test_remediation_platform_detection():
    engine = PostAuditRemediationEngine()

    # Next.js detection
    p1 = engine.detect_platform(server_headers={"x-powered-by": "Next.js 14.2"})
    assert p1 == PlatformType.NEXTJS_REACT

    # Shopify detection
    p2 = engine.detect_platform(dom_html="<script src='https://cdn.shopify.com/s/files/1.js'></script>")
    assert p2 == PlatformType.SHOPIFY

    # WordPress detection
    p3 = engine.detect_platform(dom_html="<link rel='stylesheet' href='/wp-content/themes/twentytwenty/style.css'>")
    assert p3 == PlatformType.WORDPRESS

    # Generic fallback
    p4 = engine.detect_platform(server_headers={"server": "CustomServer"})
    assert p4 == PlatformType.GENERIC_HTML


def test_remediation_task_generation():
    engine = PostAuditRemediationEngine()
    finding = {
        "finding_id": "FIND_TITLE_001",
        "title": "Missing title element",
        "affected_urls": ["https://example.com/products/item-1", "https://example.com/products/item-2"],
    }

    # Generate task for Next.js
    task = engine.generate_task_for_finding(
        finding,
        PlatformType.NEXTJS_REACT,
        rule_id="seo.title.missing",
        evidence_ids=["EV_001", "EV_002"],
    )

    assert task.task_id == "REM_FIND_TITLE_001"
    assert task.fix_type == FixType.CODE_LEVEL
    assert task.implementation.platform == PlatformType.NEXTJS_REACT
    assert "metadata" in task.implementation.code_diff_snippet
    assert task.affected_scope["total_urls"] == 2
    assert task.affected_scope["template_pattern"] == "/products/*"
    assert "re-crawl" in task.verification_protocol.lower()


@pytest.mark.asyncio
async def test_orchestrator_post_audit_synthesis(tmp_path):
    """Verifies that running an audit synthesizes both the mathematical scorecard and remediation plan."""
    db_file = str(tmp_path / "test_synth.db")
    config = AuditConfiguration(target_url="https://synth-test.com", mode=AuditMode.QUICK)
    orchestrator = SEOAuditOrchestrator(
        audit_id="audit_synth_001",
        domain="synth-test.com",
        config=config,
        db_path=db_file,
    )

    result = await orchestrator.run()
    assessment = result["canonical_assessment"]

    # Verify mathematical scorecard exists in published canonical result
    assert "mathematical_scorecard" in assessment
    scorecard = assessment["mathematical_scorecard"]
    assert scorecard["methodology_version"] == "dristik_seo_v3.0"
    assert scorecard["overall_health_score"] is not None
    assert len(scorecard["dimensions"]) == 9

    # Verify post-audit remediation tasks exist
    assert "remediation_tasks" in assessment
    remed_tasks = assessment["remediation_tasks"]
    assert len(remed_tasks) >= 1
    assert remed_tasks[0]["task_id"].startswith("REM_")
    # Without detected framework headers, stack honestly falls back to GENERIC_HTML
    assert remed_tasks[0]["implementation"]["platform"] == "GENERIC_HTML"
    assert remed_tasks[0]["implementation"]["stack_confidence"] == "GENERIC_FALLBACK"

    # With observed Next.js server headers on crawled pages, platform is honestly DETECTED
    orch_next = SEOAuditOrchestrator(
        audit_id="audit_synth_next_002",
        domain="next-synth.com",
        config=AuditConfiguration(target_url="https://next-synth.com", mode=AuditMode.QUICK),
        db_path=db_file,
        seed_pages=[
            {
                "url": "https://next-synth.com/",
                "status_code": 200,
                "headers": {"x-powered-by": "Next.js 14.2"},
                "html": "<html><head></head><body><h1>Welcome</h1></body></html>",
                "title": "",
                "h1": ["Welcome"],
                "word_count": 40,
            }
        ],
    )
    res_next = await orch_next.run()
    next_tasks = res_next["canonical_assessment"]["remediation_tasks"]
    assert len(next_tasks) >= 1
    assert next_tasks[0]["implementation"]["platform"] == "NEXTJS_REACT"
    assert next_tasks[0]["implementation"]["stack_confidence"] == "DETECTED"
