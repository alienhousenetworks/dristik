"""Integrity fixes: no fabricated metrics, DAG order, analysis-scoped vectors, honest scores."""
import json

import pytest
from fastapi.testclient import TestClient

from app.agents.runtime.registry import SPECIALIST_AGENTS_V3
from app.cognition.ground_truth import is_usable_external
from app.core.config import settings
from app.domain.enums import MetricProvenanceState
from app.domain.models import CrawlManifest
from app.evidence.models import Evidence
from app.integrations.dataforseo_provider import KeywordAndBacklinkProvider
from app.integrations.google_connectors import GoogleSearchConsoleConnector
from app.intelligence.geo.agent_readiness import _robots_signal
from app.main import app
from app.orchestration.agent_pool import topological_waves
from app.scoring.engine import ScoringEngine
from app.domain.models import BusinessProfile
from app.crawl.vector_store import VectorStore


def test_keywords_unconnected_are_not_measured():
    provider = KeywordAndBacklinkProvider(login="", password="")
    result = provider.fetch_keywords("https://example.com")
    assert result.connected is False
    assert result.provenance == MetricProvenanceState.NOT_CONNECTED
    assert result.keywords == []
    profile = provider.fetch_backlink_profile("example.com")
    assert profile.provenance == MetricProvenanceState.NOT_CONNECTED
    assert profile.domain_rating is None


def test_gsc_bad_credentials_file_is_not_measured(tmp_path):
    path = tmp_path / "not-a-service-account.json"
    path.write_text(json.dumps({"type": "service_account", "client_email": "a@b.c"}), encoding="utf-8")
    connector = GoogleSearchConsoleConnector(credentials_json=str(path))
    summary = connector.fetch_performance("https://example.com")
    assert summary.provenance != MetricProvenanceState.MEASURED
    assert summary.total_clicks == 0
    assert summary.queries == []


def test_oauth_does_not_issue_mock_codes(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    client = TestClient(app)
    response = client.get("/api/v1/connectors/google/oauth/authorize?domain=example.com", follow_redirects=False)
    assert response.status_code == 503
    assert "mock" not in response.text.lower() or "not issued" in response.text.lower()
    quick = client.post("/api/v1/connectors/google/oauth/quick-connect", json={"domain": "example.com"})
    assert quick.status_code == 400


def test_executive_agent_runs_after_ai_search_and_adversarial_is_late():
    waves = topological_waves(SPECIALIST_AGENTS_V3)
    position = {aid: index for index, wave in enumerate(waves) for aid in wave}
    assert position["ai_search.cross_engine.v3"] < position["verification.adversarial.v3"]
    assert position["verification.adversarial.v3"] < position["verification.contradiction.v3"]
    assert position["verification.contradiction.v3"] < position["strategy.executive.v3"]
    assert position["ai_search.cross_engine.v3"] < position["strategy.executive.v3"]


def test_vector_chunks_do_not_cross_audits(tmp_path):
    store = VectorStore(db_path=str(tmp_path / "vectors.db"))
    vector = [1.0] + [0.0] * 7
    store.save_chunks("acme.com", "https://acme.com/", "homepage", ["audit one"], [vector], analysis_id="run_a")
    store.save_chunks("acme.com", "https://acme.com/", "homepage", ["audit two"], [vector], analysis_id="run_b")
    only_a = store.search_similar(vector, domain="acme.com", analysis_id="run_a", top_k=5)
    assert [row["text"] for row in only_a] == ["audit one"]
    assert store.count_chunks("acme.com") == 2


def test_honest_ai_citation_stays_null_without_a_live_run():
    scores = ScoringEngine().calculate_honest_scores(
        findings=[],
        business_profile=BusinessProfile(business_name="Acme"),
    )
    assert scores.ai_readiness_score is not None
    assert scores.ai_citation_score is None
    assert scores.ai_visibility_score is None
    assert scores.ai_visibility_status == "NOT_MEASURED"
    live = ScoringEngine().calculate_honest_scores(
        findings=[],
        business_profile=BusinessProfile(business_name="Acme"),
        live_citation_score=41,
    )
    assert live.ai_citation_score == 41
    assert live.ai_visibility_status == "MEASURED"


def test_failed_external_evidence_is_not_ground_truth():
    evidence = Evidence(
        id="ext_099",
        source_type="external",
        analyzer="clearbit",
        url="https://example.com",
        text="lookup failed",
        value={"status": "FAILED", "source": "clearbit"},
        hash="abc",
    )
    assert is_usable_external(evidence) is False


def test_robots_disallow_is_missing_not_invented():
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        robots_txt_found=True,
        robots_txt_content="User-agent: GPTBot\nDisallow: /\n",
    )
    signal = _robots_signal(manifest)
    assert signal.status == "MISSING"


@pytest.mark.asyncio
async def test_agent_readiness_does_not_invent_a_score_without_pages(monkeypatch):
    async def _no_network(_url):
        from app.domain.models import AgentReadinessSignal
        return AgentReadinessSignal(key="llms_txt", status="NOT_MEASURED", summary="skipped")

    monkeypatch.setattr("app.intelligence.geo.agent_readiness._llms_txt_signal", _no_network)
    from app.intelligence.geo.agent_readiness import evaluate_agent_readiness
    report = await evaluate_agent_readiness("https://example.com", [], manifest=None)
    assert report.score is None
    assert any(signal.status == "NOT_MEASURED" for signal in report.signals)
