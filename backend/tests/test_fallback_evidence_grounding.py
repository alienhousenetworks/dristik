"""
Tests for Deterministic Fallback Engine Grounding & Business Classification
Verifies that:
1. Professional services/engineering sites with 'product' copy are NOT classified as eCommerce.
2. eCommerce requires strict transactional shopping keywords (cart/checkout).
3. Brand name, value proposition, services, and audience are dynamically extracted from DOM evidence.
"""
import pytest
from app.evidence.models import Evidence
from app.inference.fallback import DeterministicFallbackEngine

def test_services_company_with_product_copy_is_classified_as_agency():
    engine = DeterministicFallbackEngine()
    
    evidence_list = [
        Evidence(
            id="ev_001",
            source_type="meta",
            analyzer="test",
            hash="h1",
            url="https://alienhouse.in",
            value={
                "title": "Alienhouse Networks | Digital Engineering & Cloud Architecture",
                "description": "Alienhouse Networks provides premier digital engineering, cloud infrastructure, and technical consulting for enterprises."
            }
        ),
        Evidence(
            id="ev_002",
            source_type="h1",
            analyzer="test",
            hash="h2",
            url="https://alienhouse.in",
            text="Accelerating Enterprise Digital Transformation"
        ),
        Evidence(
            id="ev_003",
            source_type="h2",
            analyzer="test",
            hash="h3",
            url="https://alienhouse.in",
            text="Custom Cloud Architecture & DevOps"
        ),
        Evidence(
            id="ev_004",
            source_type="h2",
            analyzer="test",
            hash="h4",
            url="https://alienhouse.in",
            text="Enterprise Software Engineering"
        ),
        Evidence(
            id="ev_005",
            source_type="content",
            analyzer="test",
            hash="h5",
            url="https://alienhouse.in",
            text="We design and engineer resilient digital products, scalable cloud platforms, and consulting solutions for our clients."
        ),
        Evidence(
            id="ev_006",
            source_type="dom",
            analyzer="test",
            hash="h6",
            url="https://alienhouse.in",
            selector="button.cta-primary",
            text="Schedule a Consultation"
        )
    ]

    res = engine.execute_fallback("business_intelligence", evidence_list)

    # 1. Classification & Brand
    assert res["business_name"] == "Alienhouse Networks"
    assert res["primary_intent"] == "agency"
    assert res["primary_intent"] != "ecommerce"
    assert "Professional Services" in res["business_model"]

    # 2. Dynamic Value Proposition (Extracted from meta description)
    assert res["value_proposition"] == "Alienhouse Networks provides premier digital engineering, cloud infrastructure, and technical consulting for enterprises."
    assert "Curating specialized products" not in res["value_proposition"]
    assert "frictionless online ordering" not in res["value_proposition"]

    # 3. Dynamic Services (Extracted from H2s)
    assert "Custom Cloud Architecture & DevOps" in res["services"]
    assert "Enterprise Software Engineering" in res["services"]

    # 4. Dynamic CTA
    assert res["primary_cta"] == "Schedule a Consultation"

    # 5. AI Search Simulation fails closed without live search engine
    sim = engine.execute_fallback("ai_search_simulation", evidence_list)
    assert sim["status"] == "UNAVAILABLE"
    assert len(sim["evaluations"]) == 0
    assert "AI search query simulation is unavailable" in sim["notes"]

def test_strict_ecommerce_requires_cart_or_checkout():
    engine = DeterministicFallbackEngine()
    
    # Only mentions generic 'product' - should NOT be ecommerce
    evidence_product_only = [
        Evidence(
            id="ev_p1",
            source_type="meta",
            analyzer="test",
            hash="hp1",
            url="https://example.com",
            value={"title": "Tech Platform - Product Showcase"}
        ),
        Evidence(
            id="ev_p2",
            source_type="content",
            analyzer="test",
            hash="hp2",
            url="https://example.com",
            text="Learn more about our product capabilities and enterprise consulting services."
        )
    ]
    res_p = engine.execute_fallback("business_intelligence", evidence_product_only)
    assert res_p["primary_intent"] != "ecommerce"

    # With explicit add to cart and checkout - IS ecommerce
    evidence_cart = [
        Evidence(
            id="ev_c1",
            source_type="meta",
            analyzer="test",
            hash="hc1",
            url="https://shop.example.com",
            value={"title": "Artisan Apparel Store"}
        ),
        Evidence(
            id="ev_c2",
            source_type="dom",
            analyzer="test",
            hash="hc2",
            url="https://shop.example.com",
            text="Add to Cart - $49.00 - Proceed to Checkout"
        )
    ]
    res_c = engine.execute_fallback("business_intelligence", evidence_cart)
    assert res_c["primary_intent"] == "ecommerce"
