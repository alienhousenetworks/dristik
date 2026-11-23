"""Tests for Phase 2: Provider-Independent SROEngine & Gemini groundingSupports Selection Rate."""
import pytest
from app.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse
from app.geo.adapters.gemini import compute_selection_rate, parse_grounding_supports
from app.geo.models import GEOTestingMode
from app.geo.sro import SROEngine, SROStageStatus


class _StubProviderAdapter(BaseGeoEngineAdapter):
    def __init__(self, engine_id: str, display_name: str, citations: list[str], content: str, configured: bool = True):
        self.engine_id = engine_id
        self.display_name = display_name
        self.supports_web_search = True
        self._citations = citations
        self._content = content
        super().__init__(api_key="test-key" if configured else "", model="stub-v1")

    async def execute_query(self, prompt: str, locale: str = "en-US", client=None) -> EngineRawResponse:
        return EngineRawResponse(
            engine_id=self.engine_id,
            engine_name=self.display_name,
            model_version="stub-v1",
            raw_content=self._content,
            citations=self._citations,
            status_code=200,
            is_live=True,
            testing_mode=GEOTestingMode.API_WITH_SEARCH,
        )


def test_parse_grounding_supports_and_selection_rate():
    gm = {
        "webSearchQueries": ["best crm for startups", "startup crm comparison"],
        "groundingChunks": [
            {"web": {"uri": "https://www.acme.com/crm", "title": "acme.com"}},
            {"web": {"uri": "https://competitor.io/guide", "title": "competitor.io"}},
        ],
        "groundingSupports": [
            {
                "segment": {"startIndex": 0, "endIndex": 40, "text": "Acme CRM offers automated workflow routing for startups."},
                "groundingChunkIndices": [0],
                "confidenceScores": [0.94],
            },
            {
                "segment": {"startIndex": 41, "endIndex": 90, "text": "Competitor IO provides basic contact storage only."},
                "groundingChunkIndices": [1],
                "confidenceScores": [0.82],
            },
        ],
    }
    parsed = parse_grounding_supports(gm)
    assert len(parsed["chunks"]) == 2
    assert len(parsed["supports"]) == 2

    sr = compute_selection_rate("https://acme.com/crm", parsed["chunks"], parsed["supports"])
    assert sr["target_url_found"] is True
    assert sr["target_chunk_indices"] == [0]
    assert sr["target_grounding_words"] == 8
    assert sr["total_grounding_words"] == 15
    assert sr["selection_rate"] == round(8 / 15, 4)


@pytest.mark.asyncio
async def test_sro_engine_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr("app.geo.sro.get_adapter", lambda eid: None)
    monkeypatch.setattr("app.geo.sro.get_available_adapters", lambda: [])

    async def _fake_fetch(url: str, timeout: float = 10.0):
        from app.geo.sro import SROPageSnapshot
        return SROPageSnapshot(url=url, title="Acme", word_count=250, headings=["Acme CRM"])

    monkeypatch.setattr("app.geo.sro.fetch_page_snapshot", _fake_fetch)

    res = await SROEngine().analyze(target_url="https://acme.com", keyword="best crm")
    assert res.data_quality_state == "NOT_CONFIGURED"
    assert res.sample_size == 0
    assert res.overall_score is None
    assert res.organic_serp.status == SROStageStatus.NOT_CONFIGURED
    assert res.stage_results["organic_serp"].status == SROStageStatus.NOT_CONFIGURED
    assert any("Thin page content" in g for g in res.content_gaps)


@pytest.mark.asyncio
async def test_sro_runs_completely_without_gemini_with_provider_specific_metrics(monkeypatch):
    """Gemini is NOT_CONFIGURED, while Perplexity (cited) and Claude (not cited) run cleanly."""
    stubs = {
        "gemini": _StubProviderAdapter("gemini", "Google Gemini", [], "", configured=False),
        "perplexity": _StubProviderAdapter(
            "perplexity", "Perplexity Pro", ["https://acme.com/crm", "https://g2.com/acme"], "Acme CRM is widely cited."
        ),
        "claude": _StubProviderAdapter(
            "claude", "Anthropic Claude", ["https://competitor.io/crm"], "Competitor IO is an option."
        ),
    }
    monkeypatch.setattr("app.geo.sro.get_adapter", lambda eid: stubs.get(eid))
    monkeypatch.setattr("app.geo.sro.get_available_adapters", lambda: [stubs["perplexity"], stubs["claude"]])

    async def _fake_fetch(url: str, timeout: float = 10.0):
        from app.geo.sro import SROPageSnapshot
        return SROPageSnapshot(url=url, title="Page", word_count=600, headings=["Overview"])

    monkeypatch.setattr("app.geo.sro.fetch_page_snapshot", _fake_fetch)

    res = await SROEngine().analyze(
        target_url="https://acme.com/crm",
        keyword="best enterprise crm",
        brand_name="Acme",
        engines=["gemini", "perplexity", "claude"],
    )

    assert res.data_quality_state == "COMPLETED"
    assert res.sample_size == 2  # Gemini excluded from denominator because NOT_CONFIGURED
    assert res.cross_platform_selection_rate_pct == 50.0  # 1 of 2 completed providers cited target
    assert res.provider_coverage["gemini"] == "NOT_CONFIGURED"
    assert res.provider_coverage["perplexity"] == "COMPLETED"
    assert res.provider_coverage["claude"] == "COMPLETED"
    assert res.stage_results["grounding"].status == SROStageStatus.NOT_CONFIGURED
    assert res.stage_results["cross_platform_citations"].status == SROStageStatus.COMPLETED
    assert res.stage_results["organic_serp"].status == SROStageStatus.NOT_CONFIGURED
    assert len(res.evidence_refs) == 2

    by_id = {m.provider_id: m for m in res.provider_metrics}
    assert by_id["perplexity"].domain_cited is True
    assert by_id["perplexity"].brand_mentioned is True
    assert by_id["claude"].domain_cited is False
    assert by_id["claude"].brand_mentioned is False
