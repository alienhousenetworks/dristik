import pytest
from starlette.testclient import TestClient

from app.main import app
from app.seo.seo_tools import (
    check_ai_crawlers_for_target,
    validate_llms_txt,
    generate_llms_txt,
    draft_grounded_content_with_citations,
    analyze_ai_visibility_gap,
    generate_weekly_seo_checkin,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_check_ai_crawlers_for_target_robots_txt():
    robots = """
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /
"""
    result = await check_ai_crawlers_for_target("https://example.com", robots_txt=robots)
    assert result["domain"] == "example.com"
    assert result["search_retrieval_allowed"] is True
    assert result["model_training_allowed"] is False
    crawlers = {c["bot_name"]: c for c in result["crawlers"]}
    assert crawlers["GPTBot"]["is_allowed"] is False
    assert crawlers["ClaudeBot"]["is_allowed"] is False
    assert crawlers["OAI-SearchBot"]["is_allowed"] is True
    assert crawlers["PerplexityBot"]["is_allowed"] is True


def test_validate_and_generate_llms_txt():
    # Empty
    empty_res = validate_llms_txt("")
    assert empty_res["valid"] is False
    assert empty_res["score"] == 0

    # Generated
    generated = generate_llms_txt(
        biz_name="Acme Cloud",
        summary="High reliability cloud orchestration",
        canonical_domain="https://acme.example",
        sections=[{"title": "Products", "links": [{"title": "Compute", "url": "https://acme.example/compute", "description": "Serverless VM"}]}],
        faq_items=[{"question": "How much does it cost?", "answer": "Starts at $10/mo."}],
    )
    assert "# Acme Cloud" in generated
    assert "> High reliability cloud orchestration" in generated
    assert "https://acme.example/compute" in generated

    # Validate the generated output
    val_res = validate_llms_txt(generated)
    assert val_res["valid"] is True
    assert val_res["score"] >= 80
    assert val_res["links_count"] >= 3


def test_draft_grounded_content_with_citations():
    draft = draft_grounded_content_with_citations(
        topic="Enterprise Data Governance",
        brand_name="Dristik",
        domain="dristik.ai",
        key_points=["Evidence-first audits eliminate hallucinations.", "Deterministic observations ensure reproducible grades."],
    )
    assert draft["topic"] == "Enterprise Data Governance"
    assert len(draft["sources_ledger"]) >= 2
    assert "[1]" in draft["draft_markdown"]
    assert "### Verified Grounding Sources" in draft["draft_markdown"]


def test_analyze_ai_visibility_gap():
    query_evals = [
        {
            "query": "best enterprise seo platform",
            "surface": "Perplexity",
            "citations": ["https://reddit.com/r/seo", "https://g2.com/categories/seo", "https://dristik.ai"],
            "response": "Here are the top platforms: G2, Reddit, and Dristik.",
        },
        {
            "query": "alternatives to semrush",
            "surface": "ChatGPT",
            "citations": ["https://g2.com/alternatives", "https://capterra.com/compare"],
            "response": "Review sites like G2 and Capterra list alternatives.",
        },
    ]
    gap = analyze_ai_visibility_gap(
        domain="dristik.ai",
        brand_name="Dristik",
        query_evaluations=query_evals,
    )
    assert gap["total_citations"] == 5
    assert gap["first_party_citations"] == 1
    assert len(gap["sources_ai_cites_instead"]) > 0
    # G2 and Reddit should be in sources_ai_cites_instead
    domains = [s["domain"] for s in gap["sources_ai_cites_instead"]]
    assert any("g2.com" in d for d in domains)


def test_generate_weekly_seo_checkin_none():
    res = generate_weekly_seo_checkin(None)
    assert res["status"] == "NO_AUDIT_AVAILABLE"


def test_api_endpoints_tools(client):
    # 1. AI crawler checker
    res = client.post("/api/v1/tools/ai-crawler-checker", json={
        "target": "example.com",
        "robots_txt": "User-agent: *\nDisallow: /admin/\n"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["domain"] == "example.com"
    assert data["search_retrieval_allowed"] is True

    # 2. llms.txt validator
    res_val = client.post("/api/v1/tools/llms-txt-validator", json={
        "content": "# Test App\n> Testing summary\n\n## Section\n- [Link](https://test.example): Desc"
    })
    assert res_val.status_code == 200
    assert res_val.json()["valid"] is True

    # 3. Grounded content draft
    res_draft = client.post("/api/v1/tools/grounded-content-draft", json={
        "topic": "AI Visibility",
        "brand_name": "Acme",
        "domain": "acme.example"
    })
    assert res_draft.status_code == 200
    assert "sources_ledger" in res_draft.json()


@pytest.mark.asyncio
async def test_mcp_new_tools():
    from starlette.requests import Request
    from starlette.datastructures import Headers
    from fastapi import BackgroundTasks
    from app.api.routes.integrations.universal_connect import mcp_json_rpc
    from app.identity.authorizer import UserIdentity
    import json

    user = UserIdentity(org_id="org_test", email="admin@dristik.test", role="admin")

    async def mock_receive():
        return {"type": "http.request", "body": json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode("utf-8")}

    req = Request(scope={"type": "http", "method": "POST", "path": "/mcp", "headers": []}, receive=mock_receive)
    res = await mcp_json_rpc(req, BackgroundTasks(), user)
    tools = [t["name"] for t in res["result"]["tools"]]
    assert "dristik_seo_weekly_checkin" in tools
    assert "dristik_ai_crawler_check" in tools
    assert "dristik_llmstxt_tool" in tools
    assert "dristik_grounded_content_draft" in tools
    assert "dristik_ai_visibility_gap" in tools

    # Test tools/call on dristik_llmstxt_tool
    async def mock_call_receive():
        return {"type": "http.request", "body": json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "dristik_llmstxt_tool",
                "arguments": {"action": "validate", "content": "# App\n> Summary\n\n## Links\n- [Home](https://app.example): Link"}
            }
        }).encode("utf-8")}

    req_call = Request(scope={"type": "http", "method": "POST", "path": "/mcp", "headers": []}, receive=mock_call_receive)
    res_call = await mcp_json_rpc(req_call, BackgroundTasks(), user)
    call_result = res_call["result"]
    assert "structuredContent" in call_result
    assert call_result["structuredContent"]["valid"] is True

