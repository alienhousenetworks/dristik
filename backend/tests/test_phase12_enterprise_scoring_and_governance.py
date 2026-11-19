"""Tests for Phase 12 — Enterprise-Grade Scoring, Security, and Governance."""
from __future__ import annotations

import pytest

from app.governance import (
    AdversarialReviewCheck,
    AdversarialReviewVerdict,
    BenchmarkSiteProfile,
    CentralSeverityEngine,
    EnterpriseGovernanceEngine,
    EnterpriseMetricRegistry,
    IndependentAdversarialCritic,
    MetricDefinition,
    MetricDirection,
    RegressionBenchmarkLibrary,
    RemediationPriority,
    SampledMetricRecord,
    ScoringAlgorithmSpecification,
    ScoringCategory,
    ScoringGovernanceEngine,
    SeverityEvaluation,
    SeverityFactor,
    StatisticalReliabilityEngine,
)


def test_phase12_1_metric_registry_definitions_and_formulas():
    """Verify central canonical metric registry enforces definitions and blocks invented metrics."""
    registry = EnterpriseMetricRegistry()
    metrics = registry.list_metrics()
    assert len(metrics) >= 12

    # Check canonical metric attributes
    canon = registry.get_metric("SEO.TECH.001")
    assert canon is not None
    assert canon.name == "Valid Canonical Declaration Coverage"
    assert canon.category == ScoringCategory.TECHNICAL_HEALTH
    assert canon.formula == "valid_canonical_pages / eligible_inspected_pages"
    assert canon.source == "Crawl DOM Snapshot"
    assert "canonical_evidence_token" in canon.required_inputs
    assert canon.benchmark_target == 95.0
    assert canon.direction == MetricDirection.HIGHER_IS_BETTER
    assert canon.version == "v1.0"

    # Validate correct formula usage
    assert registry.validate_metric_usage("SEO.TECH.001", "valid_canonical_pages / eligible_inspected_pages") is True

    # Validate rejection of invented formula
    assert registry.validate_metric_usage("SEO.TECH.001", "some_invented_formula * 100") is False

    # Register custom metric
    custom = MetricDefinition(
        metric_id="SEC.VULN.001",
        name="Security Header Hardening Index",
        category=ScoringCategory.TECHNICAL_HEALTH,
        definition="Coverage of CSP, HSTS, and X-Content-Type headers.",
        formula="present_security_headers / required_security_headers",
        source="HTTP Response Header Inspector",
        required_inputs=["http_headers"],
        benchmark_target=100.0,
    )
    registry.register_metric(custom)
    assert registry.get_metric("SEC.VULN.001") is not None


def test_phase12_2_scoring_governance_6_dimensions_and_spec():
    """Verify 6 decoupled scoring categories, defect degradation curves, and algorithm specification."""
    engine = ScoringGovernanceEngine()

    metric_values = {
        "SEO.TECH.001": 95.0,
        "SEO.TECH.002": 0.0,
        "SEO.TECH.003": 85.0,
        "SEO.TECH.004": 100.0,
        "SEO.TECH.005": 0.0,
    }
    findings = [
        {"category": "TECHNICAL_HEALTH", "severity": "HIGH", "title": "Redirect Chain"},
        {"category": "TECHNICAL_HEALTH", "severity": "LOW", "title": "Minor header omission"},
    ]

    # Evaluate TECHNICAL_HEALTH dimension
    res = engine.evaluate_category_score(
        category=ScoringCategory.TECHNICAL_HEALTH,
        metric_values=metric_values,
        findings=findings,
    )
    assert res["category"] == "TECHNICAL_HEALTH"
    assert res["status"] == "MEASURED"
    assert res["base_score"] > 80.0
    # Penalty: HIGH (-8) + LOW (-1) = 9.0
    assert res["defect_penalty"] == 9.0
    assert res["score"] == round(res["base_score"] - 9.0, 1)
    assert "EXEMPLARY" in res["rating_tier"] or "STRONG" in res["rating_tier"]

    # Verify UNMEASURED dimension isolation (never penalized to 0.0)
    res_unmeasured = engine.evaluate_category_score(
        category=ScoringCategory.BUSINESS_PERFORMANCE,
        metric_values={},  # Zero metrics measured
    )
    assert res_unmeasured["status"] == "UNMEASURED"
    assert res_unmeasured["score"] is None
    assert "Zero relevant metric data points" in res_unmeasured["explanation"]

    # Generate dedicated Scoring Algorithm Specification Page
    spec: ScoringAlgorithmSpecification = engine.generate_scoring_algorithm_specification()
    assert spec.title == "Enterprise Scoring Algorithm & Rating Specification"
    assert spec.version == "v12.0-Enterprise"
    assert len(spec.scoring_categories) == 6
    assert "90-100" in spec.rating_tiers
    assert "<50" in spec.rating_tiers
    assert "Defect Penalty Curve" in spec.markdown_documentation
    assert "Unmeasured Data & Missing Connector Isolation" in spec.markdown_documentation


def test_phase12_3_statistical_reliability_wilson_intervals():
    """Verify mathematical Wilson score intervals and honest confidence rationales."""
    engine = StatisticalReliabilityEngine()

    # 1. Standard sample proportion (e.g. 85 / 100)
    record = engine.calculate_proportion_confidence(
        metric_id="SEO.TECH.001",
        successes=85,
        total_sample=100,
        population_size=1000,
    )
    assert record.measured_value == 85.0
    assert record.sample_size == 100
    assert record.ci_lower is not None and record.ci_upper is not None
    # 85/100 95% Wilson interval is roughly ~ [76.7%, 90.7%]
    assert 75.0 <= record.ci_lower <= 80.0
    assert 88.0 <= record.ci_upper <= 93.0
    assert "Statistically reliable sample" in record.confidence_rationale

    # 2. Exhaustive census (Sample = Population: uncertainty is 0.0)
    record_census = engine.calculate_proportion_confidence(
        metric_id="SEO.TECH.001",
        successes=50,
        total_sample=50,
        population_size=50,
    )
    assert record_census.sampling_method == "EXHAUSTIVE_CENSUS"
    assert record_census.standard_error == 0.0
    assert record_census.ci_lower == 100.0
    assert record_census.ci_upper == 100.0
    assert "zero sampling variance" in record_census.confidence_rationale

    # 3. Small exploratory sample (n < 30)
    record_small = engine.calculate_proportion_confidence(
        metric_id="AEO.CONT.001",
        successes=8,
        total_sample=10,
    )
    assert "Low-power exploratory sample" in record_small.confidence_rationale

    # 4. Continuous latency observations
    latencies = [120.0, 150.0, 180.0, 210.0, 240.0]
    record_cont = engine.calculate_continuous_confidence("SEO.TECH.003", latencies)
    assert record_cont.measured_value == 180.0
    assert record_cont.sample_size == 5
    assert record_cont.standard_error > 0.0


def test_phase12_4_severity_engine_decoupling_priority():
    """Verify central 8-factor severity engine explicitly decouples severity from remediation priority."""
    engine = CentralSeverityEngine()

    # Scenario A: Catastrophic crash bug on an ORPHAN page
    # High technical consequence (1.0), but on an orphan page (zero traffic)
    orphan_crash_factors = SeverityFactor(
        defect_scope="SINGLE_PAGE",
        technical_consequence=1.0,
        search_impact=0.9,
        security_relevance=0.8,
        user_impact=0.8,
        confidence=1.0,
        business_importance=0.2,
    )
    eval_a = engine.evaluate_severity_and_priority(
        finding_id="FIND-ORPHAN-CRASH",
        factors=orphan_crash_factors,
        traffic_tier="ORPHAN",
    )
    assert eval_a.severity_level in ("CRITICAL", "HIGH")
    assert eval_a.raw_severity_score >= 80.0
    # Decoupled Priority: Due to ORPHAN page, priority is reduced to P4 or P5
    assert eval_a.remediation_priority in (RemediationPriority.P4, RemediationPriority.P5)

    # Scenario B: Moderate defect on a HIGH traffic checkout route
    # Moderate technical consequence (0.5), but on primary checkout
    checkout_factors = SeverityFactor(
        defect_scope="SITEWIDE",
        technical_consequence=0.5,
        search_impact=0.4,
        security_relevance=0.0,
        user_impact=0.6,
        confidence=1.0,
        business_importance=1.0,
    )
    eval_b = engine.evaluate_severity_and_priority(
        finding_id="FIND-CHECKOUT-FLOW",
        factors=checkout_factors,
        traffic_tier="HIGH",
    )
    assert eval_b.severity_level == "MEDIUM"
    # Decoupled Priority: Due to SITEWIDE HIGH traffic, priority escalates to P1 or P2
    assert eval_b.remediation_priority in (RemediationPriority.P1, RemediationPriority.P2)


def test_phase12_5_adversarial_critic_9_point_review():
    """Verify independent adversarial critic executes all 9 tests and catches infractions."""
    critic = IndependentAdversarialCritic()

    ledger = {
        "ev_01": {"selector": "h1.title", "content_sha256": "abcdef123456"}
    }

    # Flawed finding set
    findings_bad = [
        # Infraction 1: Unsupported observation (no evidence token)
        {"finding_id": "F-UNSUPPORTED", "severity": "HIGH", "description": "Unbacked claim", "evidence_ids": []},
        # Infraction 2: Exaggerated severity (minor alt text marked CRITICAL)
        {"finding_id": "F-EXAGGERATED", "severity": "CRITICAL", "description": "Missing optional alt text on footer icon", "evidence_ids": ["ev_01"], "impact": "None"},
        # Infraction 3: Scope misrepresentation (1 URL described as sitewide)
        {"finding_id": "F-SCOPE", "severity": "MEDIUM", "description": "Global sitewide breakdown of all assets", "affected_urls": ["https://example.com/single-page"], "evidence_ids": ["ev_01"], "impact": "High CTR drag", "recommendation": "Fix tag immediately"},
    ]

    scores_bad = {
        "BUSINESS_PERFORMANCE": {"status": "UNMEASURED", "score": 0.0}  # Infraction: unmeasured penalized as 0.0
    }

    verdict_bad: AdversarialReviewVerdict = critic.review_report(
        report_id="rep_test_bad",
        audit_id="aud_test_bad",
        findings=findings_bad,
        evidence_ledger=ledger,
        category_scores=scores_bad,
    )

    assert verdict_bad.passed is False
    assert len(verdict_bad.infractions_found) >= 3
    infr_types = {c.infraction_type for c in verdict_bad.infractions_found}
    assert "UNSUPPORTED_OBSERVATION" in infr_types
    assert "EXAGGERATED_SEVERITY" in infr_types
    assert "SCOPE_MISREPRESENTATION" in infr_types
    assert "UNMEASURED_ZERO_CONFUSION" in infr_types

    # Clean finding set
    findings_clean = [
        {
            "finding_id": "F-CLEAN-01",
            "severity": "MEDIUM",
            "description": "Missing canonical declaration on category page.",
            "evidence_ids": ["ev_01"],
            "affected_urls": ["https://example.com/category"],
            "impact": "Potential duplicate indexation drag.",
            "recommendation": "Add canonical link tag in template head.",
        }
    ]
    scores_clean = {
        "TECHNICAL_HEALTH": {"status": "MEASURED", "score": 85.0}
    }

    verdict_clean = critic.review_report(
        report_id="rep_clean",
        audit_id="aud_clean",
        findings=findings_clean,
        evidence_ledger=ledger,
        category_scores=scores_clean,
    )
    assert verdict_clean.passed is True
    assert len(verdict_clean.infractions_found) == 0


def test_phase12_6_regression_benchmark_library_10_archetypes():
    """Verify permanent benchmark library contains 10 archetypes and verifies deterministic replay."""
    library = RegressionBenchmarkLibrary()
    profiles = library.list_profiles()
    assert len(profiles) == 10

    # Test Known-Good profile evaluation
    res_good = library.evaluate_benchmark(
        profile_id="ARCH_01_KNOWN_GOOD",
        measured_scores={"TECHNICAL_HEALTH": 95.0, "CONTENT_READINESS": 92.0},
        detected_defects=[],
    )
    assert res_good["passed"] is True
    assert len(res_good["false_positives"]) == 0
    assert len(res_good["false_negatives"]) == 0

    # Test Known-Defect profile evaluation (should detect known defects)
    res_defect = library.evaluate_benchmark(
        profile_id="ARCH_02_KNOWN_DEFECT",
        measured_scores={"TECHNICAL_HEALTH": 35.0, "CONTENT_READINESS": 30.0},
        detected_defects=["REDIRECT_LOOP", "NOINDEX_INJECTION", "BROKEN_LINKS"],
    )
    assert res_defect["passed"] is True

    # 10/10 Deterministic Replay Verification
    run_1 = {
        "scores": {"TECHNICAL_HEALTH": 84.5, "CONTENT_READINESS": 78.0},
        "findings": [{"finding_id": "F-01", "severity": "HIGH"}],
    }
    run_2 = {
        "scores": {"TECHNICAL_HEALTH": 84.5, "CONTENT_READINESS": 78.0},
        "findings": [{"finding_id": "F-01", "severity": "HIGH"}],
    }
    run_drifted = {
        "scores": {"TECHNICAL_HEALTH": 86.0, "CONTENT_READINESS": 78.0},  # drifted score
        "findings": [{"finding_id": "F-01", "severity": "HIGH"}],
    }

    assert library.verify_deterministic_replay(run_1, run_2) is True
    assert library.verify_deterministic_replay(run_1, run_drifted) is False


def test_phase12_end_to_end_governance_workflow():
    """Verify master EnterpriseGovernanceEngine executing all governance operations cohesively."""
    engine = EnterpriseGovernanceEngine()

    metric_values = {
        "SEO.TECH.001": 96.0,
        "SEO.TECH.002": 0.0,
        "SEO.TECH.003": 180.0,
        "SEO.TECH.004": 100.0,
        "SEO.TECH.005": 0.0,
        "AEO.CONT.001": 85.0,
        "AEO.CONT.002": 90.0,
        "SEO.CONT.001": 95.0,
    }

    findings = [
        {
            "finding_id": "F-GOV-01",
            "category": "TECHNICAL_HEALTH",
            "title": "Sub-optimal cache header TTL",
            "severity": "LOW",
            "technical_consequence": 0.2,
            "search_impact": 0.1,
            "security_relevance": 0.0,
            "user_impact": 0.2,
            "confidence": "VERIFIED",
            "scope": "SITEWIDE",
            "traffic_tier": "MEDIUM",
            "impact": "Slightly increased server load during traffic bursts.",
            "recommendation": "Configure Cache-Control max-age to 86400.",
            "evidence_ids": ["ev_cache_01"],
        }
    ]

    ledger = {
        "ev_cache_01": {"selector": "http.headers", "content_sha256": "9876543210fedcba"}
    }

    result = engine.run_full_governance_cycle(
        domain="governed-enterprise.com",
        audit_id="audit_gov_12",
        metric_values=metric_values,
        findings=findings,
        evidence_ledger=ledger,
    )

    assert result["domain"] == "governed-enterprise.com"
    assert result["audit_id"] == "audit_gov_12"
    assert result["governance_certified"] is True

    # 6 orthogonal category evaluations
    cats = result["category_evaluations"]
    assert len(cats) == 6
    assert cats["TECHNICAL_HEALTH"]["status"] == "MEASURED"
    assert cats["TECHNICAL_HEALTH"]["score"] >= 90.0
    assert cats["BUSINESS_PERFORMANCE"]["status"] == "UNMEASURED"

    # Evaluated findings with decoupled priority
    eval_f = result["evaluated_findings"][0]
    assert eval_f.finding_id == "F-GOV-01"
    assert eval_f.severity_level == "LOW"
    assert isinstance(eval_f.remediation_priority, RemediationPriority)

    # Algorithm specification
    spec: ScoringAlgorithmSpecification = result["algorithm_specification"]
    assert "Enterprise Scoring Algorithm" in spec.title
    assert len(spec.markdown_documentation) > 200
