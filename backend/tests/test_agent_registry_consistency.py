"""
Release-blocking tests for Phase 1: Canonical Agent Registry & Execution Coverage.
"""
import re
from pathlib import Path
import pytest

from app.orchestration.runtime.registry import (
    SPECIALIST_AGENTS_V3,
    CAPABILITY_AGENT_MAP,
    WORKFORCE_CLASSIFICATION,
    resolve_runtime_agent_id,
)
from app.orchestration.agent_pool import AgentPool
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.core.inference.model_router import ModelRouter


APP_DIR = Path(__file__).resolve().parent.parent / "app"


def test_resolve_runtime_agent_id_fails_closed():
    assert resolve_runtime_agent_id("seo.crawl.v3") == "seo.crawl.v3"
    assert resolve_runtime_agent_id("discovery") == "seo.crawl.v3"
    with pytest.raises(KeyError):
        resolve_runtime_agent_id("nonexistent.ghost.v3")


def test_capability_map_points_to_canonical_registry():
    for cap_id, aid in CAPABILITY_AGENT_MAP.items():
        assert aid in SPECIALIST_AGENTS_V3, f"Capability {cap_id} points to unknown agent {aid}"


def test_deterministic_branches_match_registry():
    src = (APP_DIR / "orchestration" / "runtime" / "specialist.py").read_text(encoding="utf-8")
    det_ids = set(re.findall(r'aid\s*==\s*"([^"]+)"', src))
    for block in re.findall(r"aid\s+in\s*\(([^)]+)\)", src, re.S):
        det_ids.update(re.findall(r'"([^"]+)"', block))

    reg_ids = set(SPECIALIST_AGENTS_V3.keys())
    dead_branches = det_ids - reg_ids
    assert not dead_branches, f"Dead deterministic branches in specialist.py: {sorted(dead_branches)}"

    unhandled = [
        aid for aid, defn in SPECIALIST_AGENTS_V3.items()
        if "deterministic" in (defn.allowed_models or []) and aid not in det_ids
    ]
    assert not unhandled, f"Deterministic-capable agents missing handler in specialist.py: {sorted(unhandled)}"


def test_reporting_and_orchestrator_have_no_broken_seo_agent_ids():
    reg_ids = set(SPECIALIST_AGENTS_V3.keys())
    for rel in [
        "seo/reporting/seo_book_renderer.py",
        "reports/plain_english_engine.py",
    ]:
        src = (APP_DIR / rel).read_text(encoding="utf-8")
        refs = set(re.findall(r'"([a-z0-9_]+\.[a-z0-9_]+(?:\.[a-z0-9_]+)?\.v3)"', src))
        missing = refs - reg_ids
        assert not missing, f"{rel} references unknown .v3 IDs: {sorted(missing)}"

    from app.reports.agentic_chapter_synthesizer import AgenticChapterSynthesizer
    seo_map_ids = {v[0] for v in AgenticChapterSynthesizer.SEO_AGENT_MAP.values()}
    missing_seo = seo_map_ids - reg_ids
    assert not missing_seo, f"SEO_AGENT_MAP references unknown .v3 IDs: {sorted(missing_seo)}"


def test_workforce_classification_present():
    assert WORKFORCE_CLASSIFICATION.get("SPECIALIST_AGENTS_V3") == "RUNTIME_AGENT"
    assert WORKFORCE_CLASSIFICATION.get("seo.enterprise") == "REFERENCE_LIBRARY"


@pytest.mark.asyncio
async def test_agent_pool_emits_execution_coverage():
    pool = AgentPool(ModelRouter())
    bb = CognitiveBlackboard(run_id="run_cov_test", website_url="https://example.com")
    summary = await pool.execute_all(bb, active_pillars={"seo"})
    cov = bb.blackboard_state.get("execution_coverage")
    assert isinstance(cov, dict)
    assert cov["registered_agents"] == len(SPECIALIST_AGENTS_V3)
    assert cov["selected_agents"] == len(SPECIALIST_AGENTS_V3)
    assert cov["skipped_agents"] == summary["skipped"]
    assert cov["executed_agents"] == summary["agents_ran"] - summary["skipped"]
    assert isinstance(cov["skipped_reasons"], dict)

