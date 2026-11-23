"""Tests for Phases 5 & 6: Battlecards, Persona Fan-Out, CLI CI gate, and Agent Discovery."""
from fastapi.testclient import TestClient

from app.cli import run_cli
from app.geo.battlecards import CompetitorBattlecardGenerator, generate_persona_fanout_prompts


def test_battlecards_grounding_and_not_measured_contract():
    empty = CompetitorBattlecardGenerator.generate(
        brand_name="Acme",
        competitors=["RivalCo"],
        responses=[],
    )
    assert empty.status == "NOT_MEASURED"
    assert empty.battlecards[0].sentiment == "not_observed"

    observed = CompetitorBattlecardGenerator.generate(
        brand_name="Acme",
        competitors=["RivalCo"],
        responses=[
            {
                "prompt": "best enterprise crm",
                "answer": "RivalCo is a leading, trusted CRM platform for enterprises.",
                "sources": ["https://g2.com/products/rivalco"],
            },
            {
                "prompt": "workflow automation crm",
                "answer": "Acme provides automated workflow orchestration for B2B teams.",
                "sources": ["https://acme.com/workflows"],
            },
        ],
    )
    assert observed.status == "OBSERVED"
    bc = observed.battlecards[0]
    assert bc.competitor == "RivalCo"
    assert bc.mention_count == 1
    assert bc.win_count == 1
    assert bc.loss_count == 1
    assert bc.sentiment == "positive"
    assert "g2.com" in bc.top_cited_domains


def test_persona_fanout_variants():
    variants = generate_persona_fanout_prompts(
        "What is the best CRM for {brand}?",
        ["CFO", "CTO", "CMO"],
        brand_name="Acme",
    )
    assert len(variants) == 3
    assert all("Acme" in v["prompt"] for v in variants)
    assert "total cost of ownership" in variants[0]["prompt"].lower()
    assert "security" in variants[1]["prompt"].lower()


def test_cli_help_json_and_ci_min_score_gate(monkeypatch, capsys):
    assert run_cli(["help", "--json"]) == 0
    out = capsys.readouterr().out
    assert '"below_min_score"' in out

    async def _fake_audit(url: str):
        return {"url": url, "score": 60.0, "summary": "mock", "signals": []}

    monkeypatch.setattr("app.cli._cmd_audit", _fake_audit)
    assert run_cli(["audit", "https://acme.com", "--json", "--min-score", "50"]) == 0
    assert run_cli(["audit", "https://acme.com", "--json", "--min-score", "80"]) == 3


def test_agent_discovery_routes_opt_in(monkeypatch):
    from app.core.config import settings
    from app.main import app

    client = TestClient(app)

    monkeypatch.setattr(settings, "ENABLE_AGENT_DISCOVERY", False)
    assert client.get("/llms.txt").status_code == 404
    assert client.get("/llms-full.txt").status_code == 404

    monkeypatch.setattr(settings, "ENABLE_AGENT_DISCOVERY", True)
    r_txt = client.get("/llms.txt")
    assert r_txt.status_code == 200
    assert "rank-signal" in r_txt.text

    r_full = client.get("/llms-full.txt")
    assert r_full.status_code == 200
    assert "dristik" in r_full.text.lower()

    r_md = client.get("/", headers={"Accept": "text/markdown"})
    assert r_md.status_code == 200
    assert "text/markdown" in r_md.headers["content-type"]
    assert "llms-txt" in r_md.headers.get("link", "")
