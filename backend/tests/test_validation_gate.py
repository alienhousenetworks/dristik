"""
Tests for Dristik AI 20-Point Validation Gate and Auto-Repair Engine.
"""
import pytest
from app.reports.validation_gate import ValidationGate, ValidationResult, BANNED_TERMS
from app.domain.models import (
    ExecutiveReport,
    Finding,
    RoadmapItem,
    CodePatch,
    BusinessProfile,
    OverallScoreResult,
    CategoryScore,
    ThreeWayComparison,
    HonestScores,
)
from app.domain.enums import Category, Severity


def create_sample_report(
    overall_score=80.0,
    weighted_sum=80.0,
    include_banned=False,
    include_duplicate_roadmap=False,
    include_patch_nulls=False,
    include_same_as_fake=False,
    include_dash_fields=False,
) -> ExecutiveReport:
    bp = BusinessProfile(
        business_name="Enterprise Platform",
        industry="SaaS",
        niche="Cloud",
        products=["Cloud Core"],
        services=["Managed Service"],
        target_audience="CTOs",
        geography="Global",
        business_model="—" if include_dash_fields else "B2B SaaS",
        value_proposition="—" if include_dash_fields else "High availability enterprise cloud infrastructure.",
    )

    scores = OverallScoreResult(
        overall_score=overall_score,
        grade="A",
        health_label="Strong",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(
                category=Category.TECHNICAL_SEO,
                score=60.0 if weighted_sum == 70.0 else 80.0,
                weight=50.0,
                weighted_score=30.0 if weighted_sum == 70.0 else 40.0,
                summary="Solid infrastructure"
            ),
            "GEO": CategoryScore(
                category=Category.GEO,
                score=80.0,
                weight=50.0,
                weighted_score=40.0,
                summary="Solid citability"
            ),
        }
    )

    story = "Enterprise Platform demonstrates consistent performance across enterprise cloud infrastructure."
    if include_banned:
        story = "Enterprise Platform offers a hyper-advanced, revolutionary platform."

    patches = []
    if include_patch_nulls:
        patches.append(CodePatch(
            patch_id="p1",
            title="Broken Schema",
            category=Category.SCHEMA,
            target_file="schema.jsonld",
            after_snippet='{"@context": "https://schema.org", "@type": "Organization", "description": null}',
            explanation="Schema fix"
        ))
    elif include_same_as_fake:
        patches.append(CodePatch(
            patch_id="p2",
            title="Social Schema",
            category=Category.SCHEMA,
            target_file="schema.jsonld",
            after_snippet='{"@context": "https://schema.org", "@type": "Organization", "name": "Test", "sameAs": ["https://twitter.com/fakeorg", "https://linkedin.com/company/fakeorg"]}',
            explanation="Social profile markup"
        ))
    else:
        patches.append(CodePatch(
            patch_id="p3",
            title="Valid Patch",
            category=Category.TECHNICAL_SEO,
            target_file="robots.txt",
            after_snippet="User-agent: *\nAllow: /",
            explanation="Robots directives"
        ))

    r7 = [RoadmapItem(
        timeframe="7_days",
        title="Fix Missing Robots Directive",
        description="Add robots.txt directives",
        impact="High",
        effort="Low",
        category=Category.TECHNICAL_SEO
    )]
    r30 = [RoadmapItem(
        timeframe="30_days",
        title="Fix Missing Robots Directive" if include_duplicate_roadmap else "Deploy Schema Microdata",
        description="Structured data rollout",
        impact="Medium",
        effort="Medium",
        category=Category.SCHEMA
    )]
    r90 = [RoadmapItem(
        timeframe="90_days",
        title="Knowledge Graph Authority",
        description="Expand knowledge graph entities",
        impact="High",
        effort="High",
        category=Category.CONTENT
    )]

    return ExecutiveReport(
        report_id="rep_test_001",
        analysis_id="run_test_001",
        website_url="https://example.com",
        domain="example.com",
        generated_at="September 20, 2026 - 12:00 UTC",
        business_profile=bp,
        scores=scores,
        story_summary=story,
        primary_strategic_opportunity="Optimize structured entity markup.",
        consultant_advice_what_to_ignore="Ignore vanity metrics.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear identity",
            search_engine_perspective="Indexable",
            ai_answer_engine_perspective="Structured"
        ),
        honest_scores=HonestScores(
            human_score=80,
            google_score=80,
            ai_citation_score=80,
            score_band="Citation Ready"
        ),
        code_patches=patches,
        roadmap_7_days=r7,
        roadmap_30_days=r30,
        roadmap_90_days=r90,
    )


def test_validation_gate_repairs_a_disagreeing_headline_score():
    report = create_sample_report()
    report.story_summary = "Enterprise Platform scores 78/100 (grade B)."
    res = ValidationGate.validate_report(report)
    assert "headline_score_matches_composite" in res.failed_checks
    repaired, repairs = ValidationGate.repair_report(report)
    assert any("dossier composite" in note for note in repairs)
    assert "78/100" not in repaired.story_summary
    again = ValidationGate.validate_report(repaired)
    assert "headline_score_matches_composite" not in again.failed_checks


def test_validation_gate_clean_report_passes():
    report = create_sample_report()
    res = ValidationGate.validate_report(report)
    assert res.is_valid is True, f"Clean report should pass gate: {res.failure_reasons}"
    assert len(res.failed_checks) == 0


def test_validation_gate_catches_arithmetic_discrepancy():
    # Overall score 80.0, but weighted sum is 70.0 (30 + 40)
    report = create_sample_report(overall_score=80.0, weighted_sum=70.0)
    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "overall_score_equals_weighted_sum" in res.failed_checks

    # Auto-repair reconciles the arithmetic
    repaired, final_res = ValidationGate.enforce_gate(report)
    assert final_res.is_valid is True
    assert repaired.scores.overall_score == 70.0


def test_validation_gate_catches_duplicate_roadmap():
    report = create_sample_report(include_duplicate_roadmap=True)
    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "zero_duplicate_roadmap_items" in res.failed_checks

    # Auto-repair removes duplicates
    repaired, final_res = ValidationGate.enforce_gate(report)
    assert final_res.is_valid is True
    # Verify title only appears in 7_days
    r30_titles = [i.title for i in repaired.roadmap_30_days]
    assert "Fix Missing Robots Directive" not in r30_titles


def test_validation_gate_catches_banned_terms():
    report = create_sample_report(include_banned=True)
    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "zero_banned_terms_in_recommended_copy" in res.failed_checks

    repaired, final_res = ValidationGate.enforce_gate(report)
    assert final_res.is_valid is True
    for term in BANNED_TERMS:
        assert term not in repaired.story_summary.lower()


def test_validation_gate_catches_patch_nulls_and_same_as():
    # Test JSON-LD null detection
    report_nulls = create_sample_report(include_patch_nulls=True)
    res_nulls = ValidationGate.validate_report(report_nulls)
    assert res_nulls.is_valid is False
    assert "all_json_ld_validates_zero_nulls" in res_nulls.failed_checks

    # Test unobserved sameAs social links
    from unittest.mock import MagicMock
    mock_manifest = MagicMock()
    mock_manifest.pages = []  # No crawled social links

    report_sameas = create_sample_report(include_same_as_fake=True)
    res_sameas = ValidationGate.validate_report(report_sameas, manifest=mock_manifest)
    assert res_sameas.is_valid is False
    assert "zero_invented_urls" in res_sameas.failed_checks

    # Auto-repair strips sameAs and nulls
    repaired, final_res = ValidationGate.enforce_gate(report_sameas, manifest=mock_manifest)
    assert final_res.is_valid is True
    assert "sameAs" not in repaired.code_patches[0].after_snippet


def test_validation_gate_directive_and_roadmap_agreement():
    report = create_sample_report()
    # Directive deprioritizes technical SEO
    report.consultant_advice_what_to_ignore = "Ignore technical SEO, XML sitemaps, and meta tags until conversion is fixed."
    # But 7-day roadmap features an XML sitemap fix and an H1 fix
    report.roadmap_7_days = [
        RoadmapItem(
            timeframe="7_days",
            title="XML sitemap was not found during crawl.",
            description="Generate sitemap.xml",
            impact="High",
            effort="Low",
            category=Category.TECHNICAL_SEO
        ),
        RoadmapItem(
            timeframe="7_days",
            title="Homepage H1 lacks commercial specificity",
            description="Clarify hero headline offer",
            impact="High",
            effort="Low",
            category=Category.CONTENT
        ),
    ]

    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "directive_and_roadmap_sequencing_agree" in res.failed_checks

    # Auto-repair resequences technical SEO to 30-day phase, leaving H1 in 7-day
    repaired, final_res = ValidationGate.enforce_gate(report)
    assert final_res.is_valid is True
    assert len(repaired.roadmap_7_days) == 1
    assert repaired.roadmap_7_days[0].title == "Homepage H1 lacks commercial specificity"
    r30_titles = [item.title for item in repaired.roadmap_30_days]
    assert "XML sitemap was not found during crawl." in r30_titles


def test_validation_gate_catches_geo_matrix_discrepancy():
    from app.domain.models import VisualIntelligencePayload, ChartSpecification
    report = create_sample_report()
    report.honest_scores.ai_citation_score = 36.0
    # Engine matrix averages to 11.25, diverging by > 1.01 pt
    matrix_chart = ChartSpecification(
        id="chart_ai_engine_matrix",
        chart_type="engine_comparison_bar",
        title="Generative Engine Citation Readiness Matrix",
        subtitle="Visibility matrix",
        ai_insight="Brand exhibits critical citation deficits across all answer engines",
        category="GEO",
        data={
            "engines": [
                {"name": "ChatGPT Search", "readiness": 0},
                {"name": "Perplexity AI", "readiness": 15},
                {"name": "Google AI Overviews", "readiness": 20},
                {"name": "Claude / Anthropic", "readiness": 10},
            ]
        }
    )
    report.visual_intelligence = VisualIntelligencePayload(
        ai_rationale="Test",
        audit_case_profile="SaaS",
        selected_visualizations=[matrix_chart],
        spotlight_metrics=[],
        available_customizations=[],
        generated_at="2026-09-22"
    )

    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "composite_scores_derivable" in res.failed_checks


def test_validation_gate_catches_contradictory_superlative():
    from app.domain.models import VisualIntelligencePayload, ChartSpecification
    report = create_sample_report()
    report.honest_scores.ai_citation_score = 36.0
    # Engine matrix where ChatGPT is 0% but insight claims ChatGPT is most extractable
    matrix_chart = ChartSpecification(
        id="chart_ai_engine_matrix",
        chart_type="engine_comparison_bar",
        title="Generative Engine Citation Readiness Matrix",
        subtitle="Visibility matrix",
        ai_insight="Brand is most extractable in ChatGPT Search (0% readiness)...",
        category="GEO",
        data={
            "engines": [
                {"name": "ChatGPT Search", "readiness": 36},
                {"name": "Perplexity AI", "readiness": 36},
                {"name": "Google AI Overviews", "readiness": 40},
                {"name": "Claude / Anthropic", "readiness": 32},
            ]
        }
    )
    report.visual_intelligence = VisualIntelligencePayload(
        ai_rationale="Test",
        audit_case_profile="SaaS",
        selected_visualizations=[matrix_chart],
        spotlight_metrics=[],
        available_customizations=[],
        generated_at="2026-09-22"
    )

    res = ValidationGate.validate_report(report)
    assert res.is_valid is False
    assert "composite_scores_derivable" in res.failed_checks


def test_validation_gate_handles_none_score_categories():
    """Verify ValidationGate handles categories with score=None (unmeasured/offline connectors) without TypeError."""
    report = create_sample_report(overall_score=80.0, weighted_sum=80.0)
    report.scores.category_scores["trust_authority"] = CategoryScore(
        category=Category.TRUST_AUTHORITY,
        score=None,
        confidence=0.0,
        weight=0.0,
        weighted_score=0.0,
        summary="Connector unavailable",
        status="NOT_MEASURED",
        provenance="CONNECTOR_UNAVAILABLE",
    )
    # Both validate_report and enforce_gate must succeed without throwing TypeError
    res = ValidationGate.validate_report(report)
    assert isinstance(res.is_valid, bool)

    repaired, gate_result = ValidationGate.enforce_gate(report)
    assert repaired is not None
    assert isinstance(gate_result.is_valid, bool)


def test_validation_gate_handles_unmeasured_ai_citation_and_matrix_reconciliation():
    """Verify ValidationGate handles unmeasured live citations without falsely flagging divergence against query matrix."""
    from app.domain.models import AiSearchQueryEvaluation
    report = create_sample_report(overall_score=80.0, weighted_sum=80.0)
    report.honest_scores.live_ai_citation_score = None
    report.honest_scores.ai_citation_score = None
    report.honest_scores.ai_readiness_score = 100.0
    report.ai_search_matrix = [
        AiSearchQueryEvaluation(
            query="best cloud mesh",
            question_type="Identity",
            evidence_quality="Moderate",
            score=2,
            detected_answer="Found some mention"
        )
    ]
    repaired, gate_result = ValidationGate.enforce_gate(report)
    assert "composite_scores_derivable" in gate_result.passed_checks



