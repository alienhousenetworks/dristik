"""
Tests for 5 AI Business Understanding Prompts, User Site Type Override & Zero-Fake GSC
"""
import pytest
from app.inference.prompt_compiler import load_prompt
from app.inference.fallback import DeterministicFallbackEngine
from app.evidence.models import Evidence
from app.intelligence.business.search_console import search_console_engine

def test_five_business_understanding_prompts_exist_and_load():
    """Verify that all 5 Big-4 consulting grade system prompts are present and loaded."""
    prompts = [
        "business_intent",
        "business_taxonomy",
        "business_catalog",
        "business_icp",
        "business_moat",
    ]
    for p in prompts:
        content = load_prompt(p)
        assert content is not None, f"Prompt {p} should load"
        assert len(content.strip()) > 50, f"Prompt {p} should have substantial instructions"

def test_user_declared_site_type_overrides_all_keyword_checks():
    """Verify that user-declared site type is treated as ground truth with zero keyword guesswork."""
    engine = DeterministicFallbackEngine()
    
    # Ambiguous site that mentions products, software, and stores
    evidence_list = [
        Evidence(
            id="ev_01",
            source_type="meta",
            analyzer="test",
            hash="h01",
            url="https://acme-agency.com",
            value={"title": "Acme Agency - Products & Software Platform"}
        ),
        Evidence(
            id="ev_02",
            source_type="content",
            analyzer="test",
            hash="h02",
            url="https://acme-agency.com",
            text="We build digital products, cloud software, and online stores for clients."
        )
    ]

    # User explicitly declared it is an Agency / Professional Services firm
    context_with_user_declaration = "Multi-Page Crawl Topology:\n/home\n\nUSER-DECLARED BUSINESS CATEGORY / INTENT (GROUND TRUTH):\nagency\n"
    res = engine.execute_fallback("business_intelligence", evidence_list, additional_context=context_with_user_declaration)

    assert res["primary_intent"] == "agency"
    assert "Professional Services" in res["business_model"]
    assert res["business_name"] == "Acme Agency"

    # User explicitly declared it is an Enterprise Solutions firm
    context_enterprise = "Multi-Page Crawl Topology:\n/home\n\nUSER-DECLARED BUSINESS CATEGORY / INTENT (GROUND TRUTH):\nenterprise_solutions\n"
    res_ent = engine.execute_fallback("business_intelligence", evidence_list, additional_context=context_enterprise)
    assert res_ent["primary_intent"] == "agency"
    assert "Enterprise Digital Engineering" in res_ent["business_model"]

def test_google_search_console_zero_fake_when_not_connected():
    """Verify that unauthenticated Search Console returns honest zero states with no fake numbers."""
    report = search_console_engine.generate_search_attribution(domain="unconnected-site.com")
    
    assert report.is_connected is False
    assert report.total_monthly_clicks == 0
    assert report.total_monthly_impressions == 0
    assert report.average_ctr == 0.0
    assert report.average_position == 0.0
    assert report.estimated_traffic_leakage_inr == 0.0
    assert report.top_ranking_keywords == []
    assert report.competitor_keyword_gaps == []
    assert "not connected" in report.connection_status_message.lower()
