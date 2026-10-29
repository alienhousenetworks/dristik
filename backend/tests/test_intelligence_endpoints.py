"""
Unit tests for Strategic Intelligence Endpoints:
- Competitor Discovery & 7-Vector Benchmark Matrix
- Google Search Console (GSC) Traffic Leakage & Causal Chains
- Multi-Engine AI Citation Tracker (ChatGPT, Perplexity, Gemini, Claude, Google AI)
- Lead Generation Commercial Void Detector & Landing Page Blueprints
- Agency Multi-Domain Workspace & White-label Decks
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_competitor_discovery_endpoint():
    # 1. Without identity or rival URLs: no invented names, rival scores are null
    response = client.get(
        "/api/v1/intelligence/competitors",
        params={"website_url": "https://acmesoftware.in"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target_domain"] == "acmesoftware.in"
    assert len(data["comparative_table"]) == 7
    assert "primary_competitive_gap" in data
    names = [c["brand_name"] for c in data["competitors"]]
    assert "Named rival required" not in names
    for row in data["comparative_table"]:
        assert row["competitor_1"] is None
        assert row["competitor_2"] is None
        assert row["competitor_3"] is None
        # Unmeasured target vectors stay null (no default 38/72)
        if row["dimension_key"] == "ai_citation":
            assert row["target_score"] is None

    # 2. When explicit competitor URLs are provided: names real, scores still null
    response_with_comps = client.get(
        "/api/v1/intelligence/competitors",
        params=[
            ("website_url", "https://acmesoftware.in"),
            ("competitor_urls", "https://rival-one.com"),
            ("competitor_urls", "https://rival-two.com")
        ]
    )
    assert response_with_comps.status_code == 200
    data2 = response_with_comps.json()
    assert data2["status"] == "AVAILABLE"
    assert len(data2["competitors"]) == 2
    assert data2["competitors"][0]["domain"] == "rival-one.com"
    assert data2["competitors"][0]["overall_score"] is None
    assert data2["comparative_table"][0]["competitor_1"] is None

def test_competitor_discovery_does_not_default_to_cdn_or_crm_giants():
    """A bakery (or any non-CDN/CRM business) must not be benchmarked against Cloudflare/HubSpot."""
    response = client.get(
        "/api/v1/intelligence/competitors",
        params={"website_url": "https://blue-ridge-bakery.example"}
    )
    assert response.status_code == 200
    data = response.json()
    domains = {c["domain"] for c in data["competitors"]}
    banned = {
        "cloudflare.com", "akamai.com", "fastly.com",
        "hubspot.com", "salesforce.com", "zendesk.com",
        "shopify.com", "paloaltonetworks.com",
    }
    assert domains.isdisjoint(banned)
    assert data.get("market_size_status") == "not_measured"
    assert "Named rival required" not in {c["brand_name"] for c in data["competitors"]}
    if data["competitors"]:
        assert data["competitors"][0].get("market_size") in (None, "")
        assert data["competitors"][0].get("overall_score") is None
    assert "TAM" not in (data.get("primary_competitive_gap") or "")
    for row in data["comparative_table"]:
        assert row["competitor_1"] is None

def test_search_console_attribution_endpoint():
    response = client.get(
        "/api/v1/intelligence/search-console",
        params={"domain": "acmesoftware.in"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "acmesoftware.in"
    assert "is_connected" in data
    assert "total_monthly_clicks" in data
    assert "causal_chains" in data
    assert len(data["causal_chains"]) > 0
    
    first_chain = data["causal_chains"][0]
    assert "technical_problem" in first_chain
    assert "search_visibility_impact" in first_chain
    assert "traffic_consequence" in first_chain
    assert "conversion_opportunity" in first_chain

def test_ai_citations_endpoint():
    from unittest.mock import patch, AsyncMock
    from app.core.config import settings
    from app.intelligence.citations.tracker import ai_citation_tracker

    # 1. Without live search API key, fails closed honestly with a next step
    with patch.object(settings, "ANTHROPIC_API_KEY", None), \
         patch.object(settings, "CLAUDE_API_KEY", None), \
         patch.object(settings, "OPENROUTER_API_KEY", None), \
         patch.object(settings, "GROQ_API_KEY", None), \
         patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "GOOGLE_API_KEY", None), \
         patch.dict("os.environ", {
             "ANTHROPIC_API_KEY": "",
             "CLAUDE_API_KEY": "",
             "AI_CITATION_CLAUDE_API_KEY": "",
             "PERPLEXITY_API_KEY": "",
             "OPENROUTER_API_KEY": "",
             "GROQ_API_KEY": "",
             "GEMINI_API_KEY": "",
             "GOOGLE_API_KEY": "",
         }, clear=False):
        response = client.get(
            "/api/v1/intelligence/ai-citations",
            params={
                "domain": "acmesoftware.in",
                "biz_name": "Acme Software",
                "niche": "FinTech SaaS"
            }
        )
    assert response.status_code == 200
    data = response.json()
    assert data["target_domain"] == "acmesoftware.in"
    assert data["total_queries_tracked"] == 0
    assert data["overall_ai_citation_score"] is None
    assert data["is_live"] is False
    assert "Live AI citation tracking is UNAVAILABLE" in data["status_message"]
    assert data.get("failure_code") == "missing_api_key"
    assert data.get("next_steps")
    assert any("OPENROUTER_API_KEY" in s or "PERPLEXITY_API_KEY" in s or "ANTHROPIC_API_KEY" in s for s in data["next_steps"])

    # 2. When live query returns results (Perplexity only; others stay off)
    mock_res = {
        "content": "Acme Software (acmesoftware.in) provides cloud billing APIs for banks.",
        "citations": ["https://acmesoftware.in/features", "https://fintech-guide.com"]
    }
    with patch.object(ai_citation_tracker, "_query_perplexity_live", new_callable=AsyncMock, return_value=mock_res), \
         patch.object(settings, "ANTHROPIC_API_KEY", None), \
         patch.object(settings, "CLAUDE_API_KEY", None), \
         patch.object(settings, "OPENROUTER_API_KEY", None), \
         patch.object(settings, "GROQ_API_KEY", None), \
         patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "GOOGLE_API_KEY", None), \
         patch.dict("os.environ", {
             "AI_CITATION_CROSS_PROVIDER": "true",
             "AI_CITATION_PERPLEXITY_ACTIVE": "true",
             "PERPLEXITY_API_KEY": "test_perp_key",
             "OPENROUTER_API_KEY": "",
             "ANTHROPIC_API_KEY": "",
             "CLAUDE_API_KEY": "",
             "AI_CITATION_CLAUDE_API_KEY": ""
         }, clear=False):
        resp_live = client.get(
            "/api/v1/intelligence/ai-citations",
            params={
                "domain": "acmesoftware.in",
                "biz_name": "Acme Software",
                "niche": "FinTech SaaS"
            }
        )
        assert resp_live.status_code == 200
        live_data = resp_live.json()
        assert live_data["is_live"] is True
        assert live_data["total_queries_tracked"] > 0
        assert live_data["overall_ai_citation_score"] is not None
        assert len(live_data["tracked_queries"]) > 0
        first_q = live_data["tracked_queries"][0]
        assert first_q["buyer_query"] != ""
        assert len(first_q["engines"]) >= 1

def test_lead_gen_opportunities_endpoint():
    response = client.get(
        "/api/v1/intelligence/lead-gen",
        params={
            "domain": "acmesoftware.in",
            "biz_name": "Acme Software",
            "niche": "FinTech Banking"
        }
    )
    assert response.status_code == 200
    opportunities = response.json()
    # Without a crawl, lead-gen must not emit canned landing-page blueprints.
    assert opportunities == []

def test_agency_workspace_endpoint():
    import uuid
    anonymous = client.get("/api/v1/intelligence/agency")
    assert anonymous.status_code == 401
    signup = client.post("/api/v1/auth/signup", json={
        "full_name": "Agency Owner",
        "email": f"agency_{uuid.uuid4().hex[:8]}@example.com",
        "password": "OwnerPass1",
        "organization_name": "Agency Org",
    })
    assert signup.status_code == 200, signup.text
    response = client.get("/api/v1/intelligence/agency")
    assert response.status_code == 200
    data = response.json()
    assert "clients" in data
    assert isinstance(data["clients"], list)
    assert data["branding"]["hide_dristik_branding"] is True
    
    # Add new real client
    add_resp = client.post(
        "/api/v1/intelligence/agency/clients",
        json={"client_name": "Zenith Cloud", "domain": "zenithcloud.io"}
    )
    assert add_resp.status_code == 200
    new_client = add_resp.json()
    assert new_client["client_name"] == "Zenith Cloud"
    assert new_client["domain"] == "zenithcloud.io"

    # Verify client now exists in workspace
    resp_after = client.get("/api/v1/intelligence/agency")
    assert resp_after.status_code == 200
    clients_list = resp_after.json()["clients"]
    assert any(c["domain"] == "zenithcloud.io" for c in clients_list)

    # Delete client and verify removal
    del_resp = client.delete(f"/api/v1/intelligence/agency/clients/{new_client['client_id']}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
