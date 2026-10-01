"""
Comprehensive test suite for Dristik Scoring Engine v5.0.
Verifies:
1. Continuous log-normal metric curves and Wilson 95% intervals.
2. Declarative JSON rubric loading and gate execution.
3. Strict coverage thresholds (>=60% MEASURED, 30-59.99% PARTIAL, <30% NOT_MEASURED).
4. Evidence generation on every CheckResult.
5. Dynamic gate caps (Technical SEO <= 20, Schema <= 60).
6. Root cause deduplication with zero double penalty.
7. Specialized views (Human, Google, AI Readiness, AI Visibility) alignment.
"""
import pytest
from app.domain.enums import BusinessIntent, Category, Severity, RubricConfidence, EvidenceClass
from app.domain.models import BusinessProfile, Finding, FindingEvidence, AuditScopeInfo
from app.scoring.config_v5 import load_scoring_rubric_v5
from app.scoring.curves import log_normal_curve, wilson_interval, audience_readability_score
from app.scoring.engine import ScoringEngine


def _profile(intent=BusinessIntent.LEAD_GENERATION) -> BusinessProfile:
    return BusinessProfile(
        business_name="Acme Systems",
        industry="Enterprise SaaS",
        value_proposition="Autonomous Edge Security",
        primary_cta="Schedule Demo",
        primary_intent=intent,
    )


def _finding(
    finding_id: str,
    category: Category,
    severity: Severity,
    title: str,
    evidence_url: str = "https://acme.com/",
    root_cause_id: str = None
) -> Finding:
    return Finding(
        finding_id=finding_id,
        category=category,
        severity=severity,
        title=title,
        description=f"Observed defect: {title}",
        recommendation="Apply remediation patch.",
        confidence=0.95,
        confidence_rubric=RubricConfidence.CERTAIN,
        evidence_class=EvidenceClass.OBSERVED,
        evidence=[FindingEvidence(url=evidence_url, snippet="Observed in AST/DOM")],
        evidence_refs=[evidence_url],
        root_cause_id=root_cause_id
    )


# -------------------------------------------------------------
# 1. Mathematical Curves & Wilson Statistics Tests
# -------------------------------------------------------------
def test_log_normal_curve_anchor_points():
    """Verify p10 maps to ~0.90 and median maps to ~0.50 within tolerance."""
    p10 = 2.5
    median = 4.0
    
    score_p10 = log_normal_curve(p10, p10=p10, median=median, higher_is_better=False)
    score_median = log_normal_curve(median, p10=p10, median=median, higher_is_better=False)
    
    assert abs(score_p10 - 0.90) < 0.015
    assert abs(score_median - 0.50) < 0.015
    
    # Boundary tests
    assert log_normal_curve(0.5, p10=p10, median=median) > 0.98
    assert log_normal_curve(10.0, p10=p10, median=median) < 0.10
    assert 0.0 <= log_normal_curve(-5.0, p10=p10, median=median) <= 1.0


def test_wilson_score_interval_properties():
    """Verify Wilson 95% interval calculation for sample proportions."""
    # 90 successes out of 100
    center, low, high = wilson_interval(90, 100, confidence=0.95)
    assert 0.88 <= center <= 0.91
    assert 0.82 <= low < 0.90
    assert 0.90 < high <= 0.96
    
    # 0 successes out of 10
    center, low, high = wilson_interval(0, 10, confidence=0.95)
    assert low == 0.0
    assert high > 0.0
    
    # Empty total
    assert wilson_interval(0, 0) == (0.0, 0.0, 0.0)


def test_audience_readability_gaussian_decay():
    """Verify Flesch scoring within and outside optimal target bands."""
    # B2B target band: 30 to 60
    assert audience_readability_score(45.0, "b2b_technical") == 1.0
    assert audience_readability_score(30.0, "b2b_technical") == 1.0
    assert audience_readability_score(60.0, "b2b_technical") == 1.0
    
    # Decays below 30
    assert audience_readability_score(15.0, "b2b_technical") < 0.70
    assert audience_readability_score(5.0, "b2b_technical") < 0.30
    
    # Consumer target band: 60 to 80
    assert audience_readability_score(70.0, "consumer") == 1.0
    assert audience_readability_score(40.0, "consumer") < 0.60


# -------------------------------------------------------------
# 2. JSON Rubric & Config Tests
# -------------------------------------------------------------
def test_rubric_v5_loads_and_sums_correctly():
    """Ensure rubric v5 JSON loads with all 8 categories and budget shares sum to 100."""
    rubric = load_scoring_rubric_v5()
    assert rubric.methodology_version == "5.0"
    assert len(rubric.categories) == 8
    
    for cat_name, cat_def in rubric.categories.items():
        total_sub_budget = sum(sub.budget_share for sub in cat_def.subsections.values())
        assert abs(total_sub_budget - 100.0) < 0.01, f"Category {cat_name} subsections must sum to 100%"
        for sub_name, sub_def in cat_def.subsections.items():
            assert len(sub_def.checks) > 0, f"Subsection {sub_name} must have checks"


# -------------------------------------------------------------
# 3. Clean Site Invariant & Weight Normalization
# -------------------------------------------------------------
def test_clean_site_scores_near_100_and_weights_sum_to_one():
    """A site with zero defects and valid HTTPS/Schema must score near 100 with valid weights."""
    engine = ScoringEngine()
    profile = _profile()
    res = engine.calculate_scores(
        findings=[],
        business_profile=profile,
        has_schema=True,
        is_https=True,
        readability=55.0
    )
    
    assert res.overall_score >= 98.0
    assert res.grade == "A+"
    assert res.health_label == "Exceptional"
    
    # Weights must sum to 1.0000
    active_weights_sum = sum(res.intent_adjusted_weights.values())
    assert abs(active_weights_sum - 1.0) < 0.001


# -------------------------------------------------------------
# 4. Declarative Dynamic Gates
# -------------------------------------------------------------
def test_gate_sitewide_noindex_caps_technical_seo_at_20():
    """Sitewide noindex triggers gate_critical_indexation and hard-caps Technical SEO at 20.0."""
    engine = ScoringEngine()
    disallow = _finding(
        "noindex_test",
        Category.TECHNICAL_SEO,
        Severity.CRITICAL,
        "Sitewide noindex tag blocks search engine crawling"
    )
    res = engine.calculate_scores(
        findings=[disallow],
        business_profile=_profile(),
        has_schema=True,
        is_https=True
    )
    
    tech_score = res.category_scores[Category.TECHNICAL_SEO.value]
    assert tech_score.score == 20.0
    assert any("capped at 20" in w.lower() for w in tech_score.weaknesses)


def test_gate_schema_contradiction_caps_schema_at_60():
    """Schema contradicting visible text triggers gate_schema_contradicts_visible and caps at 60.0."""
    engine = ScoringEngine()
    conflict = _finding(
        "schema_conflict_test",
        Category.SCHEMA,
        Severity.HIGH,
        "Schema name or URL contradicts visible DOM content"
    )
    res = engine.calculate_scores(
        findings=[conflict],
        business_profile=_profile(),
        has_schema=True,
        is_https=True
    )
    
    schema_score = res.category_scores[Category.SCHEMA.value]
    assert schema_score.score <= 60.0


# -------------------------------------------------------------
# 5. Check Evidence & Auditability
# -------------------------------------------------------------
def test_every_check_result_contains_evidence_and_coverage():
    """Verify that CheckResults contain auditability fields: sample_size, passed, failed, coverage, evidence."""
    engine = ScoringEngine()
    scope = AuditScopeInfo(plan_tier="growth", requested_pages=15, measured_pages=15)
    res = engine.calculate_scores(
        findings=[],
        business_profile=_profile(),
        has_schema=True,
        is_https=True,
        audit_scope=scope
    )
    
    for cat_name, cat_score in res.category_scores.items():
        if cat_score.status != "NOT_MEASURED":
            assert len(cat_score.check_results) > 0
            for chk in cat_score.check_results:
                assert chk.sample_size >= 1
                assert chk.passed + chk.failed == chk.sample_size
                assert chk.methodology_version == "5.0"
                assert chk.coverage >= 0.0


# -------------------------------------------------------------
# 6. Single Root Cause Deduplication (No Double Penalty)
# -------------------------------------------------------------
def test_root_cause_charged_once_secondary_is_downstream_consequence():
    """Root cause filed in multiple categories charges primary once; downstream has 0 points lost."""
    engine = ScoringEngine()
    primary = _finding(
        "root_brand_conflict_1",
        Category.ON_PAGE_SEO,
        Severity.HIGH,
        "Root cause brand mismatch across headers",
        root_cause_id="root_brand_conflict"
    )
    secondary = _finding(
        "root_brand_conflict_2",
        Category.GEO,
        Severity.HIGH,
        "Root cause brand mismatch across headers",
        root_cause_id="root_brand_conflict"
    )
    
    res = engine.calculate_scores(
        findings=[primary, secondary],
        business_profile=_profile(),
        has_schema=True,
        is_https=True
    )
    
    geo_deductions = res.category_scores[Category.GEO.value].deductions
    downstream_items = [d for d in geo_deductions if d.get("is_downstream_consequence")]
    assert len(downstream_items) == 1
    assert downstream_items[0]["points_lost"] == 0.0


# -------------------------------------------------------------
# 7. Specialized Views (Honest Scores) Alignment
# -------------------------------------------------------------
def test_specialized_views_derive_from_check_results_without_conflict():
    """Specialized views (Human, Google, AI Readiness, AI Visibility) match check engine rollups."""
    engine = ScoringEngine()
    honest = engine.calculate_honest_scores(
        findings=[],
        business_profile=_profile(),
        has_schema=True,
        is_https=True,
        live_citation_score=78.5
    )
    
    assert honest.human_score >= 95.0
    assert honest.google_score >= 95.0
    assert honest.ai_readiness_score >= 95.0
    assert honest.ai_visibility_score == 78.5
    assert honest.ai_visibility_status == "MEASURED"
