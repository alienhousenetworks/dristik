"""
Unit Tests for GEO v2 Levers, Rewrite Safety Guardrails & Keyword Stuffing Penalties.
Tests:
1. Keyword stuffing detection and 10-point penalty deduction (Aggarwal et al., KDD 2024).
2. Statistics, quotation, and citation anchor density scores.
3. Rewrite primary GEO lever tagging (SIMPLIFICATION, FLUENCY_OPTIMIZATION, etc.).
4. Strict draft approval workflow and provenance tagging.
"""
import pytest
from app.intelligence.geo.citation_passages import (
    CitationPassageAnalyzer,
    CitationPassage,
    CitationRewriteItem,
)
from app.domain.models import PageEvidence


def test_keyword_stuffing_penalization():
    analyzer = CitationPassageAnalyzer(brand_name="AlienHouse")

    # Natural text without stuffing
    clean_text = (
        "AlienHouse delivers scalable AI engineering services for enterprises. "
        "Our team specializes in low-latency FastAPI architectures and semantic retrieval pipelines."
    )
    scores_clean = analyzer._score_passage(clean_text, brand="AlienHouse")
    kw_stuffed_clean = scores_clean[11]
    kw_penalty_clean = scores_clean[12]
    assert kw_stuffed_clean is False
    assert kw_penalty_clean == 0.0

    # Keyword stuffed text repeating "AlienHouse" repeatedly in a short block
    stuffed_text = (
        "AlienHouse is the best AI agency. AlienHouse builds AI backends for AlienHouse clients. "
        "Choose AlienHouse for AlienHouse enterprise solutions."
    )
    scores_stuffed = analyzer._score_passage(stuffed_text, brand="AlienHouse")
    kw_stuffed = scores_stuffed[11]
    kw_penalty = scores_stuffed[12]
    total_score = scores_stuffed[0] + scores_stuffed[1] + scores_stuffed[2] + scores_stuffed[3] - kw_penalty

    assert kw_stuffed is True
    assert kw_penalty == 10.0
    # Penalty is deducted from total score
    assert total_score <= 90.0


def test_statistics_and_citation_anchors_scoring():
    analyzer = CitationPassageAnalyzer(brand_name="AlienHouse")
    text_with_metrics = (
        "AlienHouse operates multi-region clusters with 99.9% uptime SLA, "
        "achieving under 45ms latency across SOC 2 certified AWS cloud environments."
    )
    scores = analyzer._score_passage(text_with_metrics, brand="AlienHouse")
    stat_score = scores[8]
    anchor_score = scores[10]

    assert stat_score > 0.0
    assert anchor_score > 0.0


def test_rewrite_lever_tagging_and_approval_workflow():
    analyzer = CitationPassageAnalyzer(brand_name="AlienHouse")
    pages = [
        PageEvidence(
            url="https://alienhouse.ai/services",
            title="Services",
            body_text=(
                "We provide cutting-edge, revolutionary, game-changing software solutions. "
                "Our team builds enterprise applications with high precision."
            ),
        )
    ]

    res = analyzer.analyze(pages, brand_name="AlienHouse")
    assert len(res.passages) > 0

    if res.rewrite_recommendations:
        rec = res.rewrite_recommendations[0]
        # Must be tagged with a valid GEO lever
        assert rec.primary_geo_lever in [
            "SIMPLIFICATION",
            "FLUENCY_OPTIMIZATION",
            "STATISTICS_ADDITION",
            "QUOTATION_ADDITION",
            "CITE_SOURCES"
        ]
        # Must default to draft pending approval
        assert rec.approval_status == "DRAFT_PENDING_APPROVAL"
        # Must have provenance source matching page URL
        assert rec.provenance_source == "https://alienhouse.ai/services"
        assert rec.provenance_tag in ["SITE_EXTRACTED", "UNVERIFIED_PLACEHOLDER"]
