"""Manual pillar runs must return before the AEO simulation model call finishes."""
from __future__ import annotations

import asyncio

import pytest

from app.orchestration.orchestrator import orchestrator
from app.orchestration.pipeline_dag import GraphNodeStatus, get_pipeline_controller


def _clear(analysis_id: str) -> None:
    orchestrator._pipeline_queue.pop(analysis_id, None)
    orchestrator._pipeline_active.pop(analysis_id, None)
    orchestrator._pipeline_worker.pop(analysis_id, None)


@pytest.mark.asyncio
async def test_aeo_enqueue_returns_while_section_is_still_running(monkeypatch):
    analysis_id = "run_aeo_enqueue_async"
    started = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def slow_section(aid, section_id):
        calls.append(section_id)
        started.set()
        await release.wait()
        return {"success": True, "section_id": section_id}

    monkeypatch.setattr(orchestrator, "run_pipeline_section", slow_section)
    try:
        accepted = orchestrator.enqueue_pipeline_section(analysis_id, "aeo")
        assert accepted["success"] is True
        assert accepted["status"] == "started"
        assert accepted["section_id"] == "sec_aeo"
        assert accepted["title"]
        await asyncio.wait_for(started.wait(), timeout=1)
        duplicate = orchestrator.enqueue_pipeline_section(analysis_id, "sec_aeo")
        assert duplicate["status"] == "already_running"
        assert calls == ["sec_aeo"]
    finally:
        release.set()
        worker = orchestrator._pipeline_worker.get(analysis_id)
        if worker is not None:
            await worker
        _clear(analysis_id)


@pytest.mark.asyncio
async def test_queued_pillars_run_one_at_a_time(monkeypatch):
    analysis_id = "run_aeo_enqueue_serial"
    entered = 0
    max_entered = 0
    order = []

    async def slow_section(aid, section_id):
        nonlocal entered, max_entered
        entered += 1
        max_entered = max(max_entered, entered)
        await asyncio.sleep(0.05)
        entered -= 1
        order.append(section_id)
        return {"success": True, "section_id": section_id}

    monkeypatch.setattr(orchestrator, "run_pipeline_section", slow_section)
    try:
        first = orchestrator.enqueue_pipeline_section(analysis_id, "seo")
        second = orchestrator.enqueue_pipeline_section(analysis_id, "aeo")
        assert first["status"] == "started"
        assert second["status"] == "started"
        worker = orchestrator._pipeline_worker[analysis_id]
        await asyncio.wait_for(worker, timeout=2)
        assert order == ["sec_seo", "sec_aeo"]
        assert max_entered == 1
    finally:
        _clear(analysis_id)


@pytest.mark.asyncio
async def test_aeo_enqueue_does_not_stack_on_a_running_simulation():
    analysis_id = "run_aeo_already_simulating"
    controller = get_pipeline_controller(analysis_id)
    controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.RUNNING)
    try:
        accepted = orchestrator.enqueue_pipeline_section(analysis_id, "aeo")
        assert accepted["status"] == "already_running"
        assert not orchestrator._pipeline_queue.get(analysis_id)
        assert analysis_id not in orchestrator._pipeline_worker
    finally:
        controller.mark_node_status("node_aeo_search_simulation", GraphNodeStatus.PENDING)
        _clear(analysis_id)


def test_unknown_pillar_is_rejected_without_a_worker():
    accepted = orchestrator.enqueue_pipeline_section("run_unknown_pillar", "not-a-pillar")
    assert accepted["success"] is False
    assert "not-a-pillar" in accepted["error"]
