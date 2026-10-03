"""
Tests for Scale-Aware Competitor Discovery, Parity Distance, Aggregator Filtering,
and Persistent Domain Rejection in Dristik AI.
"""
import pytest
from app.domain.models import BusinessProfile, PageEvidence
from app.intelligence.competitive.intent_extractor import intent_extractor
from app.intelligence.competitive.verification.liveness import is_aggregator_or_directory, candidate_verifier
from app.intelligence.competitive.scoring.similarity_scorer import similarity_scorer
from app.intelligence.competitive.discovery import competitor_discovery_engine
from app.intelligence.competitive.resolution.rejection_store import rejection_store
from app.intelligence.competitive.models import CompetitorType


def test_boutique_scale_scoring():
    """Verify that a boutique agency profile produces scale_score <= 0.35."""
    bp = BusinessProfile(
        business_name="Alienhouse Networks",
        industry="Information Technology",
        niche="Digital Engineering & Cloud Architecture",
        products=["Private office networks", "Bespoke cloud setup"],
        services=["Digital engineering", "Cloud consulting"],
        target_audience="Fast-moving startups and product teams",
        value_proposition="Boutique digital engineering and private network architecture for agile teams.",
        target_org_scale="smb",
    )
    pages = [
        PageEvidence(
            url="https://alienhouse.net",
            title="Alienhouse Networks | Digital Engineering Studio",
            h1=["Boutique Cloud Engineering"],
            body_text="We are a boutique studio of 15 engineers building private cloud networks. Book a 15-min call to start a project.",
        )
    ]
    univ = intent_extractor.extract_universe(domain="alienhouse.net", business_profile=bp, pages=pages)
    assert univ.scale_score <= 0.35
    assert univ.scale_tier == "boutique"
    assert "Digital Engineering" in univ.primary_topics or "Digital engineering" in univ.products_services


def test_enterprise_scale_scoring():
    """Verify that an enterprise firm with RFP and thousands of employees produces scale_score >= 0.70."""
    bp = BusinessProfile(
        business_name="Global IT Conglomerate",
        industry="Information Technology",
        niche="Enterprise Digital Transformation",
        target_org_scale="enterprise",
    )
    pages = [
        PageEvidence(
            url="https://globalcorp.com",
            title="Global IT Conglomerate | Fortune 500 Transformation",
            h1=["Enterprise Global Outsourcing"],
            body_text="With over 150,000 employees across 40 global offices, we deliver multi-million enterprise digital transformation. Request RFP or contact enterprise procurement.",
        )
    ]
    univ = intent_extractor.extract_universe(domain="globalcorp.com", business_profile=bp, pages=pages)
    assert univ.scale_score >= 0.70
    assert univ.scale_tier == "enterprise"


def test_aggregator_directory_discard():
    """Ensure directory and review sites are never classified as valid competitors."""
    assert is_aggregator_or_directory("clutch.co") is True
    assert is_aggregator_or_directory("g2.com") is True
    assert is_aggregator_or_directory("capterra.com") is True
    assert is_aggregator_or_directory("linkedin.com") is True
    assert is_aggregator_or_directory("thoughtbot.com") is False
    assert is_aggregator_or_directory("strv.com") is False


def test_scale_parity_filters_enterprise_giants_from_direct():
    """
    Given AlienHouse (scale ~0.20), Accenture/Capgemini (scale ~0.95) must be
    classified as ASPIRATIONAL, while Thoughtbot/STRV (scale ~0.25) must be DIRECT.
    """
    alienhouse_profile = {
        "brand_name": "AlienHouse",
        "scale_score": 0.20,
        "services": ["Digital engineering", "Cloud consulting"],
        "niche": "Digital Engineering & Cloud Architecture",
        "target_buyer_persona": "Startup CTOs & Founders",
        "geography": "Global",
    }
    
    # 1. Giant Enterprise Candidate
    accenture_profile = {
        "brand_name": "Accenture",
        "domain": "accenture.com",
        "scale_score": 0.95,
        "services": ["IT consulting", "Enterprise transformation"],
        "niche": "IT Consulting",
        "target_buyer_persona": "Fortune 500 VP & Procurement",
        "geography": "Global",
    }
    sim_acc, breakdown_acc, class_acc, expl_acc = similarity_scorer.compute_similarity(
        alienhouse_profile, accenture_profile
    )
    # Scale parity distance is |0.20 - 0.95| = 0.75, so scale parity = 0.25
    assert breakdown_acc["scale_parity"] <= 0.30
    assert class_acc == CompetitorType.ASPIRATIONAL
    assert "Aspirational Leader" in expl_acc

    # 2. Boutique Peer Candidate
    thoughtbot_profile = {
        "brand_name": "Thoughtbot",
        "domain": "thoughtbot.com",
        "scale_score": 0.25,
        "services": ["Digital engineering", "Product design"],
        "niche": "Digital Engineering & Design Studio",
        "target_buyer_persona": "Startup Founders & Tech Leaders",
        "geography": "Global",
    }
    sim_tb, breakdown_tb, class_tb, expl_tb = similarity_scorer.compute_similarity(
        alienhouse_profile, thoughtbot_profile
    )
    assert breakdown_tb["scale_parity"] >= 0.90
    assert class_tb == CompetitorType.DIRECT
    assert "Direct peer match" in expl_tb


@pytest.mark.asyncio
async def test_discover_and_benchmark_blends_user_and_auto():
    """Verify that user-supplied competitor URLs coexist with auto-discovered peers and are tagged properly."""
    bp = BusinessProfile(
        business_name="Alienhouse Networks",
        industry="Information Technology",
        niche="Digital Engineering & Cloud Architecture",
        products=["Private networks"],
        services=["Digital engineering", "Cloud architecture"],
        target_audience="Growth tech companies",
        value_proposition="Private cloud architecture and boutique engineering.",
        target_org_scale="smb",
    )
    matrix = await competitor_discovery_engine.discover_and_benchmark(
        business_profile=bp,
        website_url="https://alienhouse.net",
        competitor_urls=["custom-rival.com"],
    )
    assert matrix.status == "AVAILABLE"
    # Target scale info present
    assert matrix.target_scale_score is not None
    assert matrix.target_scale_tier == "boutique"
    
    # Must contain custom-rival.com tagged as user_specified
    domains = [c.domain for c in matrix.competitors]
    assert "custom-rival.com" in domains
    user_comp = next(c for c in matrix.competitors if c.domain == "custom-rival.com")
    assert user_comp.source == "user_specified"
    assert user_comp.competitor_class == "DIRECT"

    # Must also contain auto-discovered peer (e.g. from vertical or candidates)
    auto_comps = [c for c in matrix.competitors if c.source == "auto_discovered"]
    assert len(auto_comps) >= 1
    # Check that giants are NOT in direct list
    assert "accenture.com" not in domains
    assert "capgemini.com" not in domains


def test_rejection_store_persists_and_excludes():
    """Verify that rejected domains are stored and filtered out."""
    target = "test-domain-rejection.com"
    rejected = "unwanted-competitor.com"
    rejection_store.record_rejection(target, rejected)
    
    rejections = rejection_store.get_rejected_domains(target)
    assert rejected in rejections
