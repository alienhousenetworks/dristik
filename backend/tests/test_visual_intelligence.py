"""
Tests for AI-Adaptive Visual Intelligence Engine
Verifies dynamic chart selection, AI rationale synthesis, and spotlight metrics.
"""
import pytest
from app.domain.models import (
    BusinessProfile,
    OverallScoreResult,
    CategoryScore,
    HonestScores,
    CrawlManifest,
    PageEvidence,
    Finding,
    AiSearchQueryEvaluation,
    ChartSpecification,
    VisualIntelligencePayload,
)
from app.domain.enums import Severity, Category
from app.intelligence.monitoring.visual_intelligence import VisualIntelligenceEngine

def test_visual_intelligence_case_evaluation_and_selection():
    engine = VisualIntelligenceEngine()

    # 1. Setup simulated multi-page SaaS audit with latency volatility
    pages = [
        PageEvidence(url="https://saas-example.com/", status_code=200, ttfb_ms=180.0, word_count=950),
        PageEvidence(url="https://saas-example.com/pricing", status_code=200, ttfb_ms=890.0, word_count=420),
        PageEvidence(url="https://saas-example.com/features", status_code=200, ttfb_ms=640.0, word_count=1200),
    ]
    manifest = CrawlManifest(
        domain="saas-example.com",
        base_url="https://saas-example.com",
        pages=pages,
        total_pages_discovered=3,
        crawl_health={"avg_ttfb_ms": 570}
    )

    business_profile = BusinessProfile(
        business_name="SaaS Metrics Inc",
        industry="Technology",
        niche="Cloud Analytics",
        products=["Analytics Dashboard"],
        services=["Data Integration"],
        target_audience="DevOps and CTOs",
        geography="Global",
        business_model="B2B SaaS Subscription",
        value_proposition="Real-time infrastructure observability"
    )

    scores = OverallScoreResult(
        overall_score=72.0,
        grade="B",
        health_label="Needs Optimization",
        category_scores={
            "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=82.0, weight=0.2, weighted_score=16.4, summary="Good technical foundation", strengths=["Clean HTML5"], weaknesses=[]),
            "ON_PAGE_SEO": CategoryScore(category=Category.ON_PAGE_SEO, score=78.0, weight=0.15, weighted_score=11.7, summary="Solid meta tags", strengths=[], weaknesses=[]),
            "GEO": CategoryScore(category=Category.GEO, score=42.0, weight=0.2, weighted_score=8.4, summary="Low citation rate", strengths=[], weaknesses=["No definition blocks"]),
            "UX_CONVERSION": CategoryScore(category=Category.UX_CONVERSION, score=68.0, weight=0.2, weighted_score=13.6, summary="Moderate UX", strengths=[], weaknesses=[]),
            "SCHEMA": CategoryScore(category=Category.SCHEMA, score=50.0, weight=0.15, weighted_score=7.5, summary="Basic schema", strengths=[], weaknesses=[]),
            "TRUST_AUTHORITY": CategoryScore(category=Category.TRUST_AUTHORITY, score=74.0, weight=0.1, weighted_score=7.4, summary="Trust signals present", strengths=[], weaknesses=[]),
        }
    )

    honest_scores = HonestScores(
        human_score=68,
        google_score=80,
        ai_citation_score=42,
        score_band="Fragile Presence"
    )

    findings = [
        Finding(
            finding_id="f_001",
            category=Category.GEO,
            severity=Severity.CRITICAL,
            title="Zero Direct Answer Snippets on Pricing Page",
            description="ChatGPT and Perplexity fail to extract tier definitions.",
            evidence=[],
            evidence_refs=[],
            confidence=0.92,
            confidence_label="Strong Evidence",
            impact=9,
            effort=2,
            priority=1,
            recommendation="Add 40-60 word answer definition snippet.",
            verification_status="verified"
        ),
        Finding(
            finding_id="f_002",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Pricing Page TTFB Spikes to 890ms",
            description="Exceeds Google crawl budget threshold.",
            evidence=[],
            evidence_refs=[],
            confidence=0.95,
            confidence_label="Strong Evidence",
            impact=8,
            effort=3,
            priority=2,
            recommendation="Enable edge caching.",
            verification_status="verified"
        ),
        Finding(
            finding_id="f_003",
            category=Category.SCHEMA,
            severity=Severity.HIGH,
            title="Missing SoftwareApplication JSON-LD Schema",
            description="Answer engines cannot parse application features.",
            evidence=[],
            evidence_refs=[],
            confidence=0.88,
            confidence_label="Strong Evidence",
            impact=8,
            effort=2,
            priority=3,
            recommendation="Inject SoftwareApplication schema.",
            verification_status="verified"
        ),
    ]

    ai_search_matrix = [
        AiSearchQueryEvaluation(
            query="best cloud analytics for devops",
            question_type="Offering",
            evidence_quality="Weak",
            detected_answer="Competitors cited; target domain missing definitions.",
            score=3,
            citation_probability=0.25,
        ),
        AiSearchQueryEvaluation(
            query="saas metrics inc pricing",
            question_type="Pricing",
            evidence_quality="Moderate",
            detected_answer="Self-serve mentioned but tier breakdown missing.",
            score=5,
            citation_probability=0.55,
        ),
    ]

    payload = engine.synthesize_visual_intelligence(
        domain="saas-example.com",
        business_profile=business_profile,
        scores=scores,
        honest_scores=honest_scores,
        manifest=manifest,
        findings=findings,
        ai_search_matrix=ai_search_matrix,
    )

    # 2. Assertions
    assert isinstance(payload, VisualIntelligencePayload)
    assert payload.ai_rationale is not None
    assert "saas-example.com" in payload.ai_rationale
    assert len(payload.selected_visualizations) >= 3

    # Check chart types selected by AI
    chart_types = [c.chart_type for c in payload.selected_visualizations]
    assert "radar" in chart_types
    assert "latency_curve" in chart_types
    assert "defect_donut" in chart_types
    assert "engine_comparison_bar" not in chart_types
    assert "journey_funnel" not in chart_types

    # Check spotlight numbers
    assert len(payload.spotlight_metrics) >= 4
    metric_ids = [m.id for m in payload.spotlight_metrics]
    assert "metric_avg_ttfb" in metric_ids
    assert "metric_citation_readiness" in metric_ids
    assert "metric_blocker_density" in metric_ids
