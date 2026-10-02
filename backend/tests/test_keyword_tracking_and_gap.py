"""
Unit and Integration Tests for Keyword Tracking, SERP History, Scheduler, and Keyword Gap Engine
"""
import pytest
from fastapi.testclient import TestClient

from app.domain.models import TrackedKeyword
from app.external_authority.store import ExternalStore
from app.intelligence.competitive.keyword_gap import KeywordGapEngine
from app.intelligence.serp_tracker import SerpTrackingEngine
from app.workers.scheduler import DristikScheduler
from app.main import app


@pytest.fixture
def temp_store(tmp_path):
    db_file = tmp_path / "test_keywords.db"
    return ExternalStore(str(db_file))


def test_keyword_crud_and_movement(temp_store):
    engine = SerpTrackingEngine(store=temp_store)

    # 1. Add keyword
    kw = engine.add_keyword(
        project_id="proj_1",
        domain="dristik.ai",
        keyword="AI SEO platform",
        target_url="/platform",
        intent="Commercial",
        search_volume=5400,
        cpc_usd=4.50,
        keyword_difficulty=45,
    )
    assert kw.keyword == "AI SEO platform"
    assert kw.domain == "dristik.ai"
    assert kw.current_position is None

    # 2. List keywords
    kws = engine.list_keywords("proj_1")
    assert len(kws) == 1
    assert kws[0].keyword_id == kw.keyword_id

    # 3. Record history with rank improvement (35 -> 18)
    temp_store.record_keyword_serp_history({
        "keyword_id": kw.keyword_id,
        "project_id": "proj_1",
        "domain": "dristik.ai",
        "position": 18,
        "previous_position": 35,
        "position_delta": 17,
        "ranking_url": "https://dristik.ai/platform",
        "serp_features": ["ai_overview", "featured_snippet"],
        "has_ai_overview": True,
        "has_featured_snippet": True,
        "has_local_pack": False,
        "snapshot_date": "2026-10-01",
    })

    # Verify history
    history = engine.get_history(kw.keyword_id)
    assert len(history) == 1
    assert history[0].position == 18
    assert history[0].position_delta == 17
    assert history[0].has_ai_overview is True

    # Check updated keyword
    updated = engine.list_keywords("proj_1")[0]
    assert updated.current_position == 18
    assert updated.best_position == 18

    # 4. Movement Summary
    summary = engine.calculate_movement_summary([updated])
    assert summary.total_tracked == 1
    assert summary.improved_count == 1
    assert summary.ai_overview_count == 1

    # 5. Delete keyword
    deleted = engine.remove_keyword("proj_1", kw.keyword_id)
    assert deleted is True
    assert len(engine.list_keywords("proj_1")) == 0


def test_keyword_gap_engine(temp_store):
    serp_engine = SerpTrackingEngine(store=temp_store)
    gap_engine = KeywordGapEngine(store=temp_store)

    # Setup tracked keyword where target is unranked and competitor ranks #3
    kw = serp_engine.add_keyword(
        project_id="proj_gap",
        domain="target.com",
        keyword="cloud migration services",
        intent="Commercial",
        search_volume=12000,
        cpc_usd=15.00,
        keyword_difficulty=55,
    )

    # Competitor ranks #3
    temp_store.record_keyword_competitors([{
        "keyword_id": kw.keyword_id,
        "project_id": "proj_gap",
        "competitor_domain": "competitor.com",
        "position": 3,
        "ranking_url": "https://competitor.com/cloud-migration",
        "snapshot_date": "2026-10-01",
    }])

    report = gap_engine.evaluate_gap(
        target_domain="target.com",
        competitor_domains=["competitor.com"],
        project_id="proj_gap",
    )

    assert report.target_domain == "target.com"
    assert report.total_missing_keywords >= 1
    assert report.total_opportunity_traffic > 0

    first = report.opportunities[0]
    assert first.keyword == "cloud migration services"
    assert first.competitor_rank == 3
    assert first.gap_type == "MISSING_OPPORTUNITY"
    assert "Create dedicated landing page" in first.recommended_action


@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    scheduler = DristikScheduler(check_interval_seconds=10)
    assert scheduler.is_running is False
    status = scheduler.status()
    assert status["running"] is False

    await scheduler.start()
    assert scheduler.is_running is True

    # Execute single tick
    tick_result = await scheduler.tick()
    assert "timestamp" in tick_result

    await scheduler.stop()
    assert scheduler.is_running is False


def test_keywords_fastapi_endpoints():
    with TestClient(app) as client:
        # Add keyword
        res = client.post("/api/v1/intelligence/keywords", json={
            "project_id": "test_e2e_proj",
            "domain": "acme.com",
            "keyword": "enterprise workflow automation",
            "intent": "Commercial",
            "tags": ["core", "enterprise"],
        })
        assert res.status_code == 201
        data = res.json()
        kw_id = data["keyword_id"]
        assert data["keyword"] == "enterprise workflow automation"

        # List keywords
        res = client.get("/api/v1/intelligence/keywords?project_id=test_e2e_proj")
        assert res.status_code == 200
        items = res.json()
        assert any(i["keyword_id"] == kw_id for i in items)

        # Movement summary
        res = client.get("/api/v1/intelligence/keywords/movement-summary?project_id=test_e2e_proj")
        assert res.status_code == 200

        # Gap analysis endpoint
        res = client.post("/api/v1/intelligence/keywords/gap", json={
            "target_domain": "acme.com",
            "competitor_domains": ["rival.com"],
            "project_id": "test_e2e_proj",
        })
        assert res.status_code == 200
        gap_data = res.json()
        assert "opportunities" in gap_data

        # Delete keyword
        res = client.delete(f"/api/v1/intelligence/keywords/{kw_id}?project_id=test_e2e_proj")
        assert res.status_code == 200
