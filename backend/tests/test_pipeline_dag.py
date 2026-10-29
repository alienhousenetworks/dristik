"""
Tests for Modular DAG Execution Engine, dependency prerequisites, pause/resume, and activity logging.
"""
import pytest
from app.orchestration.pipeline_dag import (
    get_pipeline_controller,
    GraphNodeStatus,
    NODES_REGISTRY,
    SECTIONS_REGISTRY,
)
from app.orchestration.orchestrator import orchestrator


def test_dag_registry_structure():
    assert len(SECTIONS_REGISTRY) == 7
    assert len(NODES_REGISTRY) >= 15
    crawl_node = NODES_REGISTRY["node_crawl"]
    assert crawl_node.dependencies == []

    dom_node = NODES_REGISTRY["node_dom_extraction"]
    assert "node_crawl" in dom_node.dependencies


def test_controller_dependency_resolution():
    analysis_id = "test_dag_analysis_001"
    ctrl = get_pipeline_controller(analysis_id)

    # Initially, node_crawl has no dependencies -> can run
    assert ctrl.are_dependencies_met("node_crawl") is True

    # node_dom_extraction requires node_crawl -> initially not met
    assert ctrl.are_dependencies_met("node_dom_extraction") is False
    assert "node_crawl" in ctrl.get_missing_dependencies("node_dom_extraction")

    # Mark node_crawl completed
    ctrl.mark_node_status("node_crawl", GraphNodeStatus.COMPLETED)
    assert ctrl.are_dependencies_met("node_dom_extraction") is True
    assert ctrl.get_missing_dependencies("node_dom_extraction") == []


def test_controller_activity_logging():
    analysis_id = "test_dag_activity_002"
    ctrl = get_pipeline_controller(analysis_id)

    event = ctrl.log_activity(
        node_id="node_crawl",
        status="running",
        action="crawl.fetch",
        summary="Fetching target pages...",
        details={"max_pages": 3}
    )
    assert event.node_id == "node_crawl"
    assert event.section_id == "sec_ingestion"
    assert len(ctrl.activity_log) > 0

    state = ctrl.get_full_graph_state()
    assert state["analysis_id"] == analysis_id
    assert "nodes" in state
    assert "sections" in state
    assert len(state["activity_events"]) > 0


def test_pause_and_resume_controller():
    analysis_id = "test_dag_pause_003"
    ctrl = get_pipeline_controller(analysis_id)

    assert ctrl.is_pause_requested() is False
    ctrl.request_pause()
    assert ctrl.is_pause_requested() is True

    ctrl.clear_pause()
    assert ctrl.is_pause_requested() is False
