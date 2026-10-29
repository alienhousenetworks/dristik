import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.domain.models import (
    ExecutiveReport,
    BusinessProfile,
    OverallScoreResult,
    Category,
    CategoryScore,
    ThreeWayComparison,
    CrawlManifest,
)
from app.intelligence.geo.benchmark_runner import GeoBenchmarkReport, ShareOfModelMetric
from app.intelligence.geo.audit_monitor import run_audit_visibility
from app.intelligence.geo.adapters.openai_search import OpenAISearchAdapter


def test_executive_report_schema_includes_benchmark_and_citations():
    scores = OverallScoreResult(
        overall_score=75.0,
        grade="B",
        band="Strong",
        confidence="HIGH",
        health_label="Calibrated",
        category_scores={"GEO": CategoryScore(category=Category.GEO, summary="GEO score", score=75.0, grade="B", weight=1.0, impact_level="MEDIUM", findings_count=0)},
    )
    report = ExecutiveReport(
        report_id="test_rep_1",
        analysis_id="test_run_1",
        manifest_id="man_1",
        website_url="https://example.com",
        domain="example.com",
        generated_at="2026-10-11 12:00:00 UTC",
        business_profile=BusinessProfile(business_name="Example"),
        scores=scores,
        story_summary="Audit for Example.",
        primary_strategic_opportunity="Opportunity text",
        consultant_advice_what_to_ignore="Ignore text",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Human perspective",
            search_engine_perspective="Search perspective",
            ai_answer_engine_perspective="AI perspective",
        ),
        crawl_manifest=CrawlManifest(domain="example.com", pages=[], total_pages=0),
        geo_benchmark_report={
            "share_of_model": {"share_of_model_pct": 65.5},
            "sentiment_audit": {"overall_sentiment_distribution": {"POSITIVE": 10}},
            "offpage_citation_summary": {"top_authority_hubs": [{"domain": "techcrunch.com"}]},
        },
        ai_citation_dashboard={
            "target_domain": "example.com",
            "overall_ai_citation_score": 78,
            "tracked_queries": [],
        },
    )
    dumped = report.model_dump()
    assert dumped["geo_benchmark_report"]["share_of_model"]["share_of_model_pct"] == 65.5
    assert dumped["ai_citation_dashboard"]["overall_ai_citation_score"] == 78


@pytest.mark.asyncio
async def test_run_audit_visibility_returns_tuple_of_scorecard_and_report(monkeypatch):
    monkeypatch.setenv("DRISTIK_AI_MONITOR_IN_TESTS", "1")

    mock_geo_report = GeoBenchmarkReport(
        benchmark_id="BENCH-123",
        target_domain="example.com",
        brand_name="Example",
        run_date="2026-10-11T12:00:00Z",
        total_queries=6,
        reproducibility_hash="hash123",
        share_of_model=ShareOfModelMetric(
            target_domain="example.com",
            brand_name="Example",
            total_evaluated_queries=6,
            share_of_model_pct=72.0,
            first_party_citation_share_pct=60.0,
            recommendation_rank_score=80.0,
        ),
    )

    with patch(
        "app.intelligence.geo.audit_monitor.get_available_adapters",
        return_value=[MagicMock(engine_id="chatgpt")],
    ), patch(
        "app.intelligence.geo.audit_monitor.benchmark_runner.execute_benchmark",
        new_callable=AsyncMock,
        return_value=mock_geo_report,
    ):
        scorecard, bench_report = await run_audit_visibility(
            domain="example.com",
            brand_name="Example",
            max_pages=1,
        )
        assert scorecard is not None
        assert bench_report is not None
        assert bench_report.benchmark_id == "BENCH-123"
        assert bench_report.share_of_model.share_of_model_pct == 72.0


@pytest.mark.asyncio
async def test_openai_search_adapter_openrouter_fallback():
    adapter = OpenAISearchAdapter(
        api_key="test_key",
        model="openai/gpt-6.1-sol",
        base_url="https://openrouter.ai/api/v1",
        engine_id="chatgpt",
        display_name="ChatGPT (OpenAI)",
    )

    mock_client = AsyncMock()
    # First call returns 404 (model not found)
    first_res = MagicMock(status_code=404, text="Model not found")
    # Second call returns 200 for fallback model
    second_res = MagicMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": "Example brand https://example.com/about"}}]},
    )
    mock_client.post.side_effect = [first_res, second_res]

    raw = await adapter.execute_query("What is Example?", client=mock_client)
    assert raw.status_code == 200
    assert "https://example.com/about" in raw.citations
    assert raw.model_version == "openai/gpt-4o-mini"
