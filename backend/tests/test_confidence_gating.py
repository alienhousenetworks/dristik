import pytest
from app.domain.models import Finding, BusinessProfile, CategoryScore, OverallScoreResult
from app.domain.enums import Category, Severity, SourceIntegrityLabel, ConfidenceBand, RubricConfidence
from app.reports.narrative import NarrativeGenerator
from app.scoring.engine import ScoringEngine
from app.scoring.scoring_rubric import get_scoring_rubric_v4


def test_scoring_rubric_schema():
    rubric = get_scoring_rubric_v4()
    assert rubric["version"] == "enterprise_web_intel_v4"
    assert len(rubric["five_pillars"]) == 5
    assert "diminishing_returns" in rubric
    assert "confidence_gating_rules" in rubric


def test_confidence_gating_excludes_single_source_from_what_is_holding_it_back():
    generator = NarrativeGenerator()
    profile = BusinessProfile(
        business_name="Test Enterprise",
        domain="test.com",
        industry="SaaS",
        value_proposition="Cloud intelligence",
        primary_cta="Start Free Trial"
    )

    unverified_finding = Finding(
        finding_id="f1",
        title="Unverified Strategic Buyer Friction",
        description="Buyer might bounce due to lack of trust.",
        recommendation="Conduct live buyer interviews.",
        category=Category.UX_CONVERSION,
        severity=Severity.CRITICAL,
        confidence=0.4,
        confidence_band=ConfidenceBand.LOW,
        confidence_rubric=RubricConfidence.GUESSING,
        source_integrity_label=SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED,
        evidence_refs=[],
        evidence=[]
    )

    verified_finding = Finding(
        finding_id="f2",
        title="XML Sitemap 404 Not Found",
        description="sitemap.xml returned HTTP 404.",
        recommendation="Deploy valid sitemap.xml at root.",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        confidence=0.95,
        confidence_band=ConfidenceBand.HIGH,
        confidence_rubric=RubricConfidence.CERTAIN,
        source_integrity_label=SourceIntegrityLabel.CORROBORATED,
        evidence_refs=["ev_sitemap"],
        evidence=[]
    )

    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        health_label="Needs Work",
        category_scores={}
    )

    narrative = generator.build_narrative(
        business_profile=profile,
        findings=[unverified_finding, verified_finding],
        scores=scores,
        synthesizer_output={}
    )

    # The verified finding MUST be in what_is_holding_it_back
    assert "XML Sitemap 404 Not Found" in narrative["what_is_holding_it_back"]
    # The unverified guessing finding MUST be excluded from what_is_holding_it_back
    assert "Unverified Strategic Buyer Friction" not in narrative["what_is_holding_it_back"]
    # The unverified finding MUST be collected into exploratory_hypotheses
    exploratory_titles = [f.title for f in narrative.get("exploratory_hypotheses", [])]
    assert "Unverified Strategic Buyer Friction" in exploratory_titles


def test_scoring_engine_caps_unverified_severity_deduction():
    engine = ScoringEngine()
    profile = BusinessProfile(
        business_name="Test Corp",
        domain="test.com",
        industry="Tech",
        value_proposition="Testing",
        primary_cta="Get Started"
    )

    unverified_critical = Finding(
        finding_id="f_unverified",
        title="Hypothetical Critical Objection",
        description="Model thinks buyers bounce",
        recommendation="Test messaging with live buyers.",
        category=Category.UX_CONVERSION,
        severity=Severity.CRITICAL,
        confidence=0.4,
        confidence_band=ConfidenceBand.LOW,
        confidence_rubric=RubricConfidence.GUESSING,
        source_integrity_label=SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED,
        evidence_refs=[]
    )

    honest_scores = engine.calculate_honest_scores(
        findings=[unverified_critical],
        business_profile=profile,
        has_schema=True,
        is_https=True,
        readability=70.0
    )

    # Normal CRITICAL deduction is 25.0 points (100 - 25 = 75).
    # But because it is SINGLE_SOURCE_UNVERIFIED, severity is capped at MEDIUM, which is 8.0 points (100 - 8 = 92).
    assert honest_scores.human_score == 92.0
