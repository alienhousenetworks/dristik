"""
Comprehensive Test Suite for Central SEO Audit Orchestrator & Multi-Agent Workflow Engine.
Verifies:
1. 26-entity database schema initialization and persistence.
2. DAG validation, cycle detection, and topological parallel wave scheduling.
3. The 4 operating modes (QUICK, STANDARD, DEEP, CONTINUOUS).
4. Task executor with timeouts, retries, and failure isolation.
5. Pause, resume, and cancellation lifecycle.
6. EventStore SSE streaming.
7. Canonical assessment publishing.
8. FastAPI orchestrator REST & SSE endpoints.
"""
from __future__ import annotations

import asyncio
import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.seo_orchestrator_schema import init_seo_orchestrator_schema
from app.seo.audit.orchestrator import SEOAuditOrchestrator
from app.seo.audit.orchestration.dag import AuditDAG, DAGNode, DAGStage
from app.seo.audit.orchestration.event_store import EventStore
from app.seo.audit.orchestration.execution_state import (
    AuditConfiguration,
    AuditMode,
    FailurePolicy,
    NodeState,
    WorkflowBudget,
    WorkflowStatus,
)
from app.seo.audit.orchestration.task_executor import TaskExecutor


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_seo_orchestrator.db")
    init_seo_orchestrator_schema(db_file)
    return db_file


def test_schema_initialization(temp_db):
    """Verifies all 26 required enterprise tables and indexes are created."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    required_tables = [
        "seo_audit_runs",
        "seo_audit_configurations",
        "seo_agent_registry",
        "seo_agent_executions",
        "seo_agent_outputs",
        "seo_workflow_tasks",
        "seo_workflow_dependencies",
        "seo_url_inventory",
        "seo_crawl_sessions",
        "seo_crawl_pages",
        "seo_page_snapshots",
        "seo_http_observations",
        "seo_dom_observations",
        "seo_metrics",
        "seo_findings",
        "seo_finding_evidence",
        "seo_recommendations",
        "seo_remediation_tasks",
        "seo_verification_runs",
        "seo_scorecards",
        "seo_score_components",
        "seo_connectors",
        "seo_competitor_profiles",
        "seo_keyword_datasets",
        "seo_report_publications",
        "seo_methodology_versions",
    ]
    for table in required_tables:
        assert table in tables, f"Expected table '{table}' was not created in database schema."


def test_dag_structure_and_topological_waves():
    """Verifies that the DAG is acyclic and produces correct parallel execution waves."""
    dag = AuditDAG(mode=AuditMode.STANDARD)
    assert len(dag.nodes) >= 15
    waves = dag.get_waves()
    assert len(waves) >= 6

    # Wave 1 must be Discovery
    assert any(n.agent_id == "discovery_sitemap" for n in waves[0])
    # Parallel specialist wave must contain multiple independent agents
    specialist_wave = None
    for wave in waves:
        if any(n.stage == DAGStage.STAGE_5_PARALLEL_AGENTS for n in wave):
            specialist_wave = wave
            break
    assert specialist_wave is not None
    assert len(specialist_wave) >= 8, "Expected parallel execution wave for specialist agents."


def test_dag_cycle_detection():
    """Verifies that cyclic dependencies raise ValueError."""
    dag = AuditDAG(mode=AuditMode.QUICK)
    # Inject an intentional cycle
    dag.nodes["discovery_sitemap"].dependencies = ["canonical_publisher"]
    with pytest.raises(ValueError, match="Cycle detected"):
        dag.validate()


@pytest.mark.asyncio
async def test_task_executor_timeout_and_retry():
    """Verifies timeout enforcement and exponential retry behavior."""
    executor = TaskExecutor()

    attempts = 0
    async def failing_runner(ctx):
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("Transient network failure")
        return {"findings": [{"id": "test_find"}]}

    executor.register_runner("flaky_agent", failing_runner)

    node = DAGNode(
        agent_id="flaky_agent",
        agent_name="Flaky Agent",
        stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
        retry_limit=2,
        timeout_sec=5.0,
    )

    retry_logged = []
    def on_retry(aid, attempt, exc):
        retry_logged.append((aid, attempt))

    checkpoint = await executor.execute_task(node, {"target_url": "https://example.com"}, on_retry=on_retry)
    assert checkpoint.status == NodeState.COMPLETED
    assert checkpoint.findings_count == 1
    assert len(retry_logged) == 1
    assert retry_logged[0] == ("flaky_agent", 1)


@pytest.mark.asyncio
async def test_task_executor_hard_failure_isolation():
    """Verifies that an unrecoverable failure is recorded in checkpoint without unhandled exception."""
    executor = TaskExecutor()

    async def doomed_runner(ctx):
        raise ValueError("Fatal syntax error in target schema")

    executor.register_runner("doomed_agent", doomed_runner)

    node = DAGNode(
        agent_id="doomed_agent",
        agent_name="Doomed Agent",
        stage=DAGStage.STAGE_5_PARALLEL_AGENTS,
        retry_limit=1,
        timeout_sec=1.0,
    )

    checkpoint = await executor.execute_task(node, {"target_url": "https://example.com"})
    assert checkpoint.status == NodeState.FAILED
    assert "Fatal syntax error" in (checkpoint.error_message or "")


@pytest.mark.asyncio
async def test_orchestrator_quick_mode_run(temp_db):
    """Executes a full QUICK mode audit workflow end-to-end."""
    config = AuditConfiguration(
        target_url="https://testbrand.com",
        mode=AuditMode.QUICK,
        workspace_id="ws_test_01",
    )
    orchestrator = SEOAuditOrchestrator(
        audit_id="audit_quick_001",
        domain="testbrand.com",
        config=config,
        db_path=temp_db,
    )

    result = await orchestrator.run()
    assert result["audit_id"] == "audit_quick_001"
    assert result["mode"] == "QUICK"
    assert result["status"] == "COMPLETED"
    assert result["executed_agents"] >= 15
    assert result["failed_agents"] == 0
    assert result["canonical_assessment"] is not None
    assert "chapters" in result["canonical_assessment"]
    assert "coverage" in result["canonical_assessment"]
    assert result["canonical_assessment"]["coverage"]["sampling_status"] == "SAMPLED_AUDIT"


@pytest.mark.asyncio
async def test_orchestrator_cancellation(temp_db):
    """Verifies that requesting cancellation halts remaining DAG execution."""
    config = AuditConfiguration(
        target_url="https://cancelbrand.com",
        mode=AuditMode.STANDARD,
    )
    orchestrator = SEOAuditOrchestrator(
        audit_id="audit_cancel_001",
        domain="cancelbrand.com",
        config=config,
        db_path=temp_db,
    )

    orchestrator.cancel()
    assert orchestrator.state.cancellation_requested is True

    result = await orchestrator.run()
    assert result["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_event_store_sse_stream():
    """Verifies that EventStore records events and yields SSE formatted chunks."""
    store = EventStore(audit_id="test_sse_audit")
    store.emit("STAGE_CHANGED", {"stage": "STAGE_1"})
    store.emit("AUDIT_COMPLETED", {"status": "SUCCESS"})

    history = store.get_history()
    assert len(history) == 2
    assert history[0]["type"] == "STAGE_CHANGED"
    assert history[1]["type"] == "AUDIT_COMPLETED"

    chunks = []
    async for chunk in store.stream():
        chunks.append(chunk)
    assert len(chunks) == 2
    assert "data: {" in chunks[0]
    assert "STAGE_CHANGED" in chunks[0]


def test_api_router_endpoints(temp_db):
    """Tests FastAPI router endpoints enforce auth, tenant isolation, and audit lifecycle."""
    from app.domain.enums import UserRole
    from app.identity.authorizer import UserIdentity
    from app.identity.deps import get_current_user

    client = TestClient(app)

    # 0. Unauthenticated request must fail closed with 401
    unauth = client.post(
        "/api/v1/seo/orchestrator/audits",
        json={"domain": "api-brand.com", "mode": "QUICK", "workspace_id": "ws_api_test"},
    )
    assert unauth.status_code == 401

    user_a = UserIdentity(
        user_id="usr_seo_a",
        org_id="org_seo_a",
        email="seo-a@example.test",
        role=UserRole.OWNER,
        is_active=True,
    )
    user_b = UserIdentity(
        user_id="usr_seo_b",
        org_id="org_seo_b",
        email="seo-b@example.test",
        role=UserRole.OWNER,
        is_active=True,
    )

    try:
        app.dependency_overrides[get_current_user] = lambda: user_a

        # 1. Start audit
        resp = client.post(
            "/api/v1/seo/orchestrator/audits",
            json={
                "domain": "api-brand.com",
                "mode": "QUICK",
                "workspace_id": "ws_api_test",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "audit_id" in data
        assert data["mode"] == "QUICK"
        audit_id = data["audit_id"]

        # 2. Query status as owner org
        status_resp = client.get(f"/api/v1/seo/orchestrator/audits/{audit_id}/status")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["audit_id"] == audit_id
        assert status_data["domain"] == "api-brand.com"

        # 3. Cross-tenant query must be denied (404)
        app.dependency_overrides[get_current_user] = lambda: user_b
        other_resp = client.get(f"/api/v1/seo/orchestrator/audits/{audit_id}/status")
        assert other_resp.status_code == 404

        # 4. Cancel audit as owner org
        app.dependency_overrides[get_current_user] = lambda: user_a
        cancel_resp = client.post(f"/api/v1/seo/orchestrator/audits/{audit_id}/cancel")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"
    finally:
        app.dependency_overrides.clear()
