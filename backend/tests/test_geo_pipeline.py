"""
Unit tests for Dristik AI GEO/AEO Time-Series Pipeline Store & Runner.
"""
import os
import tempfile
import pytest
from app.geo.pipeline_store import (
    GeoPipelineStore,
    GeoQueryRecord,
)
from app.geo.pipeline_runner import (
    _extract_ordinal_position,
    FIXED_PROMPT_SET,
)


@pytest.fixture
def temp_store():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_geo.db")
        store = GeoPipelineStore(db_path=db_path)
        yield store


def test_ordinal_position_extraction():
    text1 = """Here are the top alternatives:
1. CompetitorA - Best for enterprise
2. AlienHouse - Premier secure network provider
3. CompetitorB - Entry level"""
    pos1 = _extract_ordinal_position(text1, "AlienHouse", "alienhousenetworks.com")
    assert pos1 == 2

    text2 = "We recommend #1 AlienHouse Networks for deep infrastructure."
    pos2 = _extract_ordinal_position(text2, "AlienHouse", "alienhousenetworks.com")
    assert pos2 == 1

    text3 = "No numbered list here, just general commentary."
    pos3 = _extract_ordinal_position(text3, "AlienHouse", "alienhousenetworks.com")
    assert pos3 is None


def test_fixed_prompts_structure():
    assert len(FIXED_PROMPT_SET) == 6
    query_ids = [p["query_id"] for p in FIXED_PROMPT_SET]
    assert query_ids == ["Q-01", "Q-02", "Q-03", "Q-04", "Q-05", "Q-06"]
    for p in FIXED_PROMPT_SET:
        assert "{brand}" in p["template"]


def test_snapshot_lifecycle_and_delta_tracking(temp_store):
    domain = "alienhousenetworks.com"
    brand = "AlienHouse Networks"
    industry = "Enterprise Networking"

    # 1. First Snapshot (Baseline)
    q1 = GeoQueryRecord(
        query_id="Q-01",
        buyer_query="What is AlienHouse Networks?",
        commercial_intent="Brand Identity & Offering",
        engine_id="perplexity",
        engine_name="Perplexity Pro",
        raw_response_text="AlienHouse Networks provides zero-trust mesh routing.",
        was_mentioned=True,
        mention_position=1,
        was_cited=False,
        cited_urls=[],
        competitor_cited_instead=None,
        extractability_health="FAIR"
    )

    snap1 = temp_store.save_snapshot(
        snapshot_id="snap_001",
        domain=domain,
        brand_name=brand,
        industry=industry,
        overall_score=45,
        engine_scores={"Perplexity Pro": 45.0},
        critical_blindspots=["Pricing & Commercial Model"],
        query_results=[q1],
        engines_measured_count=1,
        timestamp="2026-09-01T10:00:00Z"
    )

    assert snap1.overall_score == 45
    assert snap1.delta_score is None
    assert snap1.query_results[0].delta_vs_previous == "BASELINE"

    # 2. Second Snapshot (Subsequent run with citation improvement)
    q1_v2 = GeoQueryRecord(
        query_id="Q-01",
        buyer_query="What is AlienHouse Networks?",
        commercial_intent="Brand Identity & Offering",
        engine_id="perplexity",
        engine_name="Perplexity Pro",
        raw_response_text="AlienHouse Networks (https://alienhousenetworks.com) is verified.",
        was_mentioned=True,
        mention_position=1,
        was_cited=True,
        cited_urls=["https://alienhousenetworks.com/overview"],
        competitor_cited_instead=None,
        extractability_health="EXCELLENT"
    )

    snap2 = temp_store.save_snapshot(
        snapshot_id="snap_002",
        domain=domain,
        brand_name=brand,
        industry=industry,
        overall_score=75,
        engine_scores={"Perplexity Pro": 75.0},
        critical_blindspots=[],
        query_results=[q1_v2],
        engines_measured_count=1,
        timestamp="2026-09-08T10:00:00Z"
    )

    # Verify score delta
    assert snap2.overall_score == 75
    assert snap2.delta_score == 30  # 75 - 45
    # Verify per-query delta
    assert snap2.query_results[0].delta_vs_previous == "+NEW CITATION"

    # 3. Retrieve history
    history = temp_store.get_domain_history(domain)
    assert len(history) == 2
    assert history[0].snapshot_id == "snap_001"
    assert history[1].snapshot_id == "snap_002"
    assert history[1].delta_score == 30

    # 4. Detail inspection
    detail = temp_store.get_snapshot_detail("snap_002")
    assert detail is not None
    assert len(detail.query_results) == 1
    assert detail.query_results[0].was_cited is True
    assert "https://alienhousenetworks.com/overview" in detail.query_results[0].cited_urls

    # 5. Tracked domains listing
    domains = temp_store.list_tracked_domains()
    assert len(domains) == 1
    assert domains[0]["domain"] == domain
    assert domains[0]["snapshot_count"] == 2
    assert domains[0]["latest_score"] == 75
    assert domains[0]["latest_delta"] == 30
