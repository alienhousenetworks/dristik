"""
Unit and integration tests for the unified Dristik Competitive Intelligence Engine.
Tests demand intent extraction, domain normalization, multi-signal classification,
dynamic 2D coordinates calculation, and causal advantage explanations.
Zero-fake verification: Absence of evidence fails closed to UNMEASURED.
"""
import pytest
from app.domain.models import BusinessProfile, CommercialQueryEvaluation, PageEvidence
from app.intelligence.competitive.intent_extractor import intent_extractor
from app.intelligence.competitive.engine import competitive_intelligence_engine
from app.intelligence.competitive.gaps.causal_explainer import causal_gap_explainer
from app.intelligence.competitive.metrics.geo_metrics import geo_metrics_calculator
from app.intelligence.competitive.metrics.search_metrics import search_metrics_calculator
from app.intelligence.competitive.metrics.technical_metrics import technical_metrics_calculator
from app.intelligence.competitive.models import (
    CompetitorType,
    EvidenceConfidence,
)
from app.intelligence.competitive.resolution.classifier import competitor_classifier
from app.intelligence.competitive.resolution.domain_normalizer import (
    extract_brand_from_domain,
    is_valid_competitor_domain,
    normalize_domain,
)
from app.intelligence.competitive.scoring.landscape_calculator import landscape_calculator


def test_domain_normalizer():
    assert normalize_domain("https://www.alienhousenetworks.com/pricing/") == "alienhousenetworks.com"
    assert normalize_domain("http://TailScale.com:443") == "tailscale.com"
    assert normalize_domain("tryprofound.com/audit") == "tryprofound.com"

    assert extract_brand_from_domain("tryprofound.com") == "Profound"
    assert extract_brand_from_domain("alien-house.com") == "Alien House"
    assert extract_brand_from_domain("tailscale.com") == "Tailscale"

    assert is_valid_competitor_domain("tailscale.com", "alienhousenetworks.com") is True
    assert is_valid_competitor_domain("alienhousenetworks.com", "alienhousenetworks.com") is False
    assert is_valid_competitor_domain("google.com", "alienhousenetworks.com") is False


def test_intent_extractor():
    bp = BusinessProfile(
        business_name="Acme Cloud",
        industry="Cybersecurity",
        niche="Zero Trust Network Access",
        products=["ZTNA Gateway", "Mesh VPN"],
        services=["Enterprise Deployment"],
        target_audience="DevOps and CISOs",
    )
    pages = [
        PageEvidence(
            url="https://acmecloud.com",
            title="Acme Cloud | Modern Zero Trust Mesh VPN",
            h1=["Secure Zero Trust Network Platform for Enterprise"],
            schema_types=["SoftwareApplication", "Organization"],
        )
    ]

    universe = intent_extractor.extract_universe(
        domain="acmecloud.com",
        business_profile=bp,
        pages=pages,
    )

    assert universe.brand_name == "Acme Cloud"
    assert universe.target_domain == "acmecloud.com"
    assert any("zero trust" in t.lower() for t in universe.primary_topics)
    assert len(universe.discovery_seed_queries) > 0


def test_competitor_classifier():
    # Direct match
    types_direct = competitor_classifier.classify_competitor(
        domain="rival.com",
        overlap_signals={"keyword_overlap_pct": 45.0, "ai_prompt_overlap_pct": 35.0, "is_direct_offer_match": True},
    )
    assert CompetitorType.DIRECT in types_direct
    assert CompetitorType.SEARCH in types_direct
    assert CompetitorType.GEO in types_direct

    # Search only
    types_search = competitor_classifier.classify_competitor(
        domain="searchrival.com",
        overlap_signals={"keyword_overlap_pct": 20.0, "ai_prompt_overlap_pct": 5.0},
    )
    assert CompetitorType.SEARCH in types_search
    assert CompetitorType.DIRECT not in types_search


def test_dynamic_landscape_coordinates_calculation():
    # Tested metrics
    search_dim, _ = search_metrics_calculator.compute_search_score(
        competitor_id="c1",
        target_queries=["mesh vpn", "zero trust software"],
        competitor_ranking_queries={"mesh vpn": 2, "zero trust software": 4},
    )
    geo_dim, _ = geo_metrics_calculator.compute_geo_score(
        competitor_id="c1",
        competitor_domain="c1.com",
        total_prompts_tested=10,
        prompt_mentions=6,
        citations_count=5,
    )

    coords = landscape_calculator.compute_coordinates(search_dim=search_dim, geo_dim=geo_dim)

    # Coordinates must be continuous numbers between 0.0 and 1.0, not hardcoded constants
    assert 0.0 <= coords.x <= 1.0
    assert 0.0 <= coords.y <= 1.0
    assert coords.x_confidence in [EvidenceConfidence.HIGH, EvidenceConfidence.MEDIUM]
    assert coords.y_confidence in [EvidenceConfidence.HIGH, EvidenceConfidence.MEDIUM]


def test_fail_closed_zero_fake_unmeasured():
    # An uncrawled competitor must stay UNMEASURED without inventing numbers
    tech_dim, ev = technical_metrics_calculator.compute_technical_score(
        competitor_id="uncrawled_rival",
        pages=None,
    )
    assert tech_dim.status == "UNMEASURED"
    assert tech_dim.score is None
    assert tech_dim.confidence == EvidenceConfidence.UNMEASURED
    assert len(ev) == 0


def test_causal_explainer():
    target_dims = {
        "technical": technical_metrics_calculator.compute_technical_score("target", [
            PageEvidence(url="https://target.com", ttfb_ms=850.0, schema_types=["Organization"])
        ])[0],
        "geo": geo_metrics_calculator.compute_geo_score("target", "target.com", 10, 2, 1)[0],
    }

    comp_dims = {
        "technical": technical_metrics_calculator.compute_technical_score("comp", [
            PageEvidence(url="https://comp.com", ttfb_ms=210.0, schema_types=["Organization", "FAQPage", "Product"])
        ])[0],
        "geo": geo_metrics_calculator.compute_geo_score("comp", "comp.com", 10, 8, 7)[0],
    }

    expl = causal_gap_explainer.explain_advantages(
        target_domain="target.com",
        target_brand="Target Inc",
        target_dimensions=target_dims,
        competitor_domain="comp.com",
        competitor_name="Fast Rival",
        competitor_dimensions=comp_dims,
    )

    assert len(expl.reasons_they_outperform) > 0
    # Must explain faster latency or richer schema
    assert any("faster" in r.lower() or "schema" in r.lower() or "prompt" in r.lower() for r in expl.reasons_they_outperform)


def test_full_dristik_competitive_report_generation():
    bp = BusinessProfile(
        business_name="Alienhouse Networks",
        industry="Enterprise Networking",
        niche="Zero Trust Mesh Routing",
        competitors=["tailscale.com", "cloudflare.com"],
    )
    target_pages = [
        PageEvidence(
            url="https://alienhousenetworks.com",
            title="Alienhouse Networks | Enterprise Mesh",
            h1=["High Performance Mesh Networks"],
            ttfb_ms=250.0,
            schema_types=["Organization"],
            word_count=800,
        )
    ]
    comp_pages_map = {
        "tailscale.com": [
            PageEvidence(
                url="https://tailscale.com",
                title="Tailscale · Secure Network Mesh",
                h1=["WireGuard Mesh for Enterprise"],
                ttfb_ms=180.0,
                schema_types=["Organization", "SoftwareApplication", "FAQPage"],
                word_count=1200,
            )
        ]
    }
    evals = [
        CommercialQueryEvaluation(
            question_key="identity",
            question_title="Identity",
            buyer_query="What core problem does Alienhouse Networks solve?",
            before_score=8,
            before_answer="Alienhouse Networks provides mesh routing.",
            before_evidence_status="VERIFIED",
        )
    ]

    report = competitive_intelligence_engine.build_competitive_report(
        target_domain="alienhousenetworks.com",
        business_profile=bp,
        target_pages=target_pages,
        competitor_domains=["tailscale.com"],
        competitor_pages_map=comp_pages_map,
        commercial_evaluations=evals,
    )

    assert report.target_domain == "alienhousenetworks.com"
    assert report.target_brand == "Alienhouse Networks"
    assert len(report.competitors) >= 1
    assert "tailscale.com" in [c.canonical_domain for c in report.competitors]
    assert len(report.gap_matrix) > 0
    assert len(report.evidence_table) > 0
    assert "alienhousenetworks.com" in report.landscape_coordinates
    assert "tailscale.com" in report.landscape_coordinates
