"""
Integration tests for Phase 3: Live AI Citation Engine and Developer Sync Engine.
"""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.orchestration.orchestrator import orchestrator
from app.domain.models import AnalysisRun
from app.domain.enums import AnalysisStage

client = TestClient(app)


def test_live_ai_citation_query_bank():
    res = client.post("/api/v1/intelligence/ai-citations/query-bank", json={
        "domain": "linear.app",
        "queries": ["best issue tracking software", "modern project management tool"],
        "engines": ["perplexity", "chatgpt"],
        "competitors": ["jira.com", "asana.com"],
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["domain"] == "linear.app"
    assert data["total_queries"] == 2
    assert data["total_evaluations"] == 4
    assert "share_of_voice_percentage" in data
    assert len(data["evaluations"]) == 4
    # Without API keys, all citations should be NOT_AVAILABLE (zero-fake)
    assert data["total_citations"] == 0
    assert data["share_of_voice_percentage"] == 0.0


def test_live_ai_citation_single_query():
    res = client.get("/api/v1/intelligence/ai-citations/live", params={
        "domain": "linear.app",
        "query": "linear issue tracking",
        "engine": "perplexity",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["domain"] == "linear.app"
    # Without API keys configured, citation results are honest NOT_AVAILABLE
    assert data["is_cited"] is False
    assert data["citation_rank"] is None
    assert data["notice"] is not None


def test_developer_sync_github_pr():
    res = client.post("/api/v1/remediation/github/create-pr", json={
        "repo": "linear/web",
        "finding_id": "find_schema_01",
        "target_file": "app/layout.tsx",
        "patch_code": "<Script type='application/ld+json'>{...}</Script>",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "PR_CREATED"
    assert "pull" in data["pr_url"]
    assert data["files"][0]["path"] == "app/layout.tsx"


def test_developer_sync_jira_issue():
    res = client.post("/api/v1/remediation/jira/create-issue", json={
        "project_key": "SEO",
        "finding_id": "find_schema_01",
        "title": "Missing Schema Markup",
        "severity": "critical",
        "impact_explanation": "Impedes AI search comprehension.",
        "remediation_advice": "Inject Organization Schema.",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ISSUE_CREATED"
    assert data["issue_key"].startswith("SEO-")
    assert "[CRITICAL]" in data["summary"]


def test_developer_sync_linear_issue():
    res = client.post("/api/v1/remediation/linear/create-issue", json={
        "project_key": "LIN",
        "finding_id": "find_canonical_01",
        "title": "Canonical Link Dropped",
        "severity": "high",
        "impact_explanation": "Causes index dilution.",
        "remediation_advice": "Restore canonical link tag.",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "ISSUE_CREATED"
    assert data["issue_id"].startswith("LIN-")
    assert data["priority"] == 2  # high priority mapped to 2


def test_executive_deck_report():
    now = datetime.now(timezone.utc).isoformat()
    analysis_id = "run_deck_test_01"
    run = AnalysisRun(
        analysis_id=analysis_id,
        org_id="org_test",
        website_url="https://linear.app",
        status=AnalysisStage.COMPLETED,
        created_at=now,
        updated_at=now,
    )
    orchestrator.runs[analysis_id] = run

    # 1. HTML deck
    res_html = client.get(f"/api/v1/reports/{analysis_id}/executive-deck")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "DRISTIK AI // ENTERPRISE INTELLIGENCE" in res_html.text

    # 2. JSON deck metadata
    res_json = client.get(f"/api/v1/reports/{analysis_id}/executive-deck?format=json")
    assert res_json.status_code == 200
    assert res_json.json()["status"] == "READY"
