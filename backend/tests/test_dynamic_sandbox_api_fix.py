"""
Test suite for Dynamic Question Sandbox API fixes and resilience.
Verifies that:
1. `generate_audit_dynamic_sandbox` handles `page_reports` safely without AttributeError.
2. `generate_audit_dynamic_sandbox` uses `crawl_manifest.pages` directly when available.
3. `CognitiveSimulatorWorker` synthesizes 100 dynamic sandbox questions even when commercial eval LLM response is empty.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.models import (
    PageReport,
    PageSeoAudit,
    PageCopyAudit,
    PageUxSignals,
    PageEvidence,
    CrawlManifest,
    ExecutiveReport,
    AnalysisRun,
    BusinessProfile,
    ResolvedEntity,
)
from app.api.routes.audits.analyses import generate_audit_dynamic_sandbox
from app.workers.simulator_worker import CognitiveSimulatorWorker
from app.cognition.blackboard import CognitiveBlackboard


@pytest.mark.asyncio
async def test_generate_audit_dynamic_sandbox_with_page_reports_no_attribute_error(monkeypatch):
    """
    PageReport instances do not have `meta_description`, `h1`, `body_text`.
    This test verifies that `generate_audit_dynamic_sandbox` extracts fields
    safely using getattr without throwing an AttributeError.
    """
    page_rep = PageReport(
        url="https://acme-cybersecurity.io",
        page_type="homepage",
        title="Acme Cybersecurity | Enterprise Zero Trust",
        overall_score=85.0,
        seo=PageSeoAudit(),
        copywriting=PageCopyAudit(),
        ux=PageUxSignals(),
        findings=[]
    )

    report = ExecutiveReport.model_construct(
        report_id="test-rep-123",
        analysis_id="test-run-123",
        website_url="https://acme-cybersecurity.io",
        domain="acme-cybersecurity.io",
        page_reports=[page_rep],
        story_summary="Acme Cybersecurity delivers autonomous endpoint defense and compliance.",
        business_profile=BusinessProfile(business_name="Acme Cybersecurity", niche="Cybersecurity SaaS"),
        resolved_entity=ResolvedEntity(name="Acme Cybersecurity", domain="acme-cybersecurity.io", niche="Cybersecurity SaaS"),
        crawl_manifest=None,
        dynamic_sandbox_evaluations=[],
        kie_graph_summary=None,
        five_dimension_ai_visibility=None
    )

    run = AnalysisRun.model_construct(
        analysis_id="test-run-123",
        website_url="https://acme-cybersecurity.io",
        domain="acme-cybersecurity.io",
        report=report
    )

    # Mock _get_org_run to return our test run
    monkeypatch.setattr("app.api.routes.audits.analyses._get_org_run", lambda aid, user=None: run)
    mock_save = MagicMock()
    monkeypatch.setattr("app.api.routes.audits.analyses.orchestrator.repository.save_run", mock_save)

    response = await generate_audit_dynamic_sandbox(analysis_id="test-run-123", user=None)

    assert response["status"] == "AVAILABLE"
    assert response["total_questions"] == 100
    assert len(response["evaluations"]) == 100
    assert run.report.dynamic_sandbox_evaluations is not None
    assert len(run.report.dynamic_sandbox_evaluations) == 100
    assert run.report.kie_graph_summary is not None
    assert mock_save.called


@pytest.mark.asyncio
async def test_generate_audit_dynamic_sandbox_with_crawl_manifest_pages(monkeypatch):
    """
    Verifies that when `crawl_manifest.pages` exists, the endpoint uses the
    rich PageEvidence list directly.
    """
    pe = PageEvidence(
        url="https://cloudstream.dev",
        title="CloudStream | Real-Time Kafka Observability",
        h1=["Real-Time Kafka Event Streaming"],
        h2=["Scalable Cloud Ingestion"],
        body_text="CloudStream monitors event streams across clusters with sub-second latency.",
        word_count=120
    )

    manifest = CrawlManifest(
        domain="cloudstream.dev",
        base_url="https://cloudstream.dev",
        pages=[pe]
    )

    report = ExecutiveReport.model_construct(
        report_id="test-rep-456",
        analysis_id="test-run-456",
        website_url="https://cloudstream.dev",
        domain="cloudstream.dev",
        crawl_manifest=manifest,
        page_reports=[],
        business_profile=BusinessProfile(business_name="CloudStream", niche="Data Infrastructure"),
        resolved_entity=ResolvedEntity(name="CloudStream", domain="cloudstream.dev", niche="Data Infrastructure"),
        dynamic_sandbox_evaluations=[],
        kie_graph_summary=None,
        five_dimension_ai_visibility=None
    )

    run = AnalysisRun.model_construct(
        analysis_id="test-run-456",
        website_url="https://cloudstream.dev",
        domain="cloudstream.dev",
        report=report
    )

    monkeypatch.setattr("app.api.routes.audits.analyses._get_org_run", lambda aid, user=None: run)
    mock_save = MagicMock()
    monkeypatch.setattr("app.api.routes.audits.analyses.orchestrator.repository.save_run", mock_save)

    response = await generate_audit_dynamic_sandbox(analysis_id="test-run-456", user=None)

    assert response["status"] == "AVAILABLE"
    assert response["total_questions"] == 100
    assert len(response["evaluations"]) == 100
    assert run.report.kie_graph_summary is not None
    assert mock_save.called


@pytest.mark.asyncio
async def test_simulator_worker_generates_sandbox_when_raw_evals_empty():
    """
    Verifies that CognitiveSimulatorWorker generates 100 dynamic sandbox questions
    even if the model router returns empty commercial evaluations.
    """
    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={})  # Empty LLM response

    worker = CognitiveSimulatorWorker(worker_id="test_sim", model_router=mock_router)
    blackboard = CognitiveBlackboard(run_id="run_empty_llm", website_url="https://empty-eval.io")
    blackboard.resolved_entity = ResolvedEntity(name="EmptyEval Platform", domain="empty-eval.io", niche="Software Development")
    blackboard.pages = [
        PageEvidence(
            url="https://empty-eval.io",
            title="EmptyEval Platform",
            body_text="EmptyEval Platform is an automated developer tooling platform."
        )
    ]

    res = await worker.execute_task("ai_search_simulation", blackboard)

    # Dynamic sandbox evaluations should STILL be generated!
    assert len(blackboard.dynamic_sandbox_evaluations) == 100
    assert len(res["dynamic_sandbox_evaluations"]) == 100
    assert res["status"] == "AVAILABLE"
