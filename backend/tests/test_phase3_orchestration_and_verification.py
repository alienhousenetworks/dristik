"""Phase 3 tests: Pipeline ordering, ToolBus section/finding access, hybrid AI specialists,
Frontier AI deterministic finding verification, and batched 100% critic coverage.
"""
import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.enums import Category, Severity, VerificationStatus
from app.domain.evidence.models import Evidence
from app.domain.models import BusinessProfile, Claim, Finding, PageEvidence, PageSection
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.orchestrator import AnalysisOrchestrator
from app.orchestration.runtime.registry import get_agent_definition
from app.orchestration.runtime.specialist import SpecialistAgent
from app.orchestration.runtime.tool_bus import AgentToolBus
from app.workers.critic_worker import CognitiveCriticWorker


def _make_blackboard_with_sections_and_findings() -> CognitiveBlackboard:
    bb = CognitiveBlackboard(run_id="phase3_test_run", website_url="https://acme.example")
    bb.business_profile = BusinessProfile(
        business_name="Acme Cloud",
        industry="B2B SaaS",
        business_model="Subscription SaaS",
        target_audience="VP Engineering",
    )
    page = PageEvidence(
        url="https://acme.example/pricing",
        title="Pricing — Acme Cloud",
        h1=["Transparent Pricing"],
        word_count=420,
        status_code=200,
        body_text="Transparent Pricing for engineering teams. Starts at $49/month.",
        sections=[
            PageSection(
                section_id="sec_hero",
                order=0,
                section_role="hero",
                heading_text="Transparent Pricing",
                heading_level="h1",
                body_text="Starts at $49/month with SOC 2 Type II compliance.",
                word_count=9,
                ctas=["Start Free Trial"],
            ),
            PageSection(
                section_id="sec_faq",
                order=1,
                section_role="faq",
                heading_text="Billing FAQ",
                heading_level="h2",
                body_text="You can cancel any time from the billing portal.",
                word_count=9,
            ),
        ],
    )
    bb.pages = [page]
    ev = Evidence(
        id="ev_pricing_001",
        source_type="page_section",
        analyzer="crawler",
        url=page.url,
        selector="section#sec_hero",
        text="Starts at $49/month with SOC 2 Type II compliance.",
        content_sha256="a" * 64,
        hash="a" * 64,
    )
    bb.evidence_store.add(ev)
    bb.blackboard_state["deterministic_findings"] = [
        Finding(
            finding_id="det_seo_01",
            category=Category.TECHNICAL_SEO,
            severity=Severity.HIGH,
            title="Missing canonical tag on /pricing",
            description="Canonical tag absent on https://acme.example/pricing",
            affected_urls=["https://acme.example/pricing"],
            evidence_refs=["ev_pricing_001"],
            recommendation="Add self-referencing canonical link tag.",
        ),
        Finding(
            finding_id="det_cro_01",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="Pricing page lacks trust badges near CTA",
            description="No security proof adjacent to primary CTA.",
            affected_urls=["https://acme.example/pricing"],
            evidence_refs=["ev_pricing_001"],
            recommendation="Place SOC 2 badge beside CTA.",
        ),
    ]
    return bb


def test_tool_bus_exposes_sections_and_deterministic_findings():
    bb = _make_blackboard_with_sections_and_findings()
    bus = AgentToolBus(bb)

    sec_res = bus.search_site_sections(query="SOC 2 pricing", limit=5)
    assert sec_res["total_sections_indexed"] == 2
    assert len(sec_res["results"]) >= 1
    assert sec_res["results"][0]["section_id"] == "sec_hero"
    assert sec_res["results"][0]["url"] == "https://acme.example/pricing"

    seo_det = bus.get_deterministic_findings(pillar="seo", limit=10)
    assert len(seo_det["results"]) == 1
    assert seo_det["results"][0]["finding_id"] == "det_seo_01"

    all_det = bus.get_deterministic_findings(limit=10)
    assert len(all_det["results"]) == 2


@pytest.mark.asyncio
async def test_hybrid_specialist_runs_ai_after_deterministic_no_short_circuit():
    bb = _make_blackboard_with_sections_and_findings()
    spec = get_agent_definition("seo.crawl.v3")
    assert spec is not None
    assert "deterministic" in spec.allowed_models
    assert "reasoning_model" in spec.allowed_models

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={"status": "unavailable", "claims": []})

    agent = SpecialistAgent(spec, mock_router)
    result = await agent.run(bb)

    # Frontier AI MUST be called after deterministic telemetry — never short-circuited
    assert mock_router.generate_structured.await_count == 1
    call_kwargs = mock_router.generate_structured.await_args.kwargs
    assert "LAYER-0 DETERMINISTIC MEASUREMENTS" in call_kwargs["task_contract"]
    assert "STAGE-1 PYTHON ANALYZER FINDINGS" in call_kwargs["task_contract"]
    assert result["status"] in ("completed", "unavailable", "unmeasured")


@pytest.mark.asyncio
async def test_stage1b_ai_verifier_batches_verdicts_and_preserves_raw_findings():
    bb = _make_blackboard_with_sections_and_findings()
    findings = []
    for i in range(18):
        findings.append(
            Finding(
                finding_id=f"det_f_{i:02d}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=f"Deterministic check #{i}",
                description=f"Observed condition #{i} on pricing page",
                affected_urls=["https://acme.example/pricing"],
                evidence_refs=["ev_pricing_001"],
            )
        )
    bb.blackboard_state["deterministic_findings"] = findings

    batch_calls = []

    async def _fake_generate_structured(**kwargs):
        batch_calls.append(kwargs)
        assert kwargs["capability"] == "seo_verification"
        assert kwargs["model_tier"] == "reasoning_model"
        prompt = kwargs["task_contract"]
        items = []
        for f in findings:
            if f'"{f.finding_id}"' in prompt:
                if f.finding_id == "det_f_00":
                    items.append({
                        "finding_id": f.finding_id,
                        "verdict": "FALSE_POSITIVE",
                        "business_impact_rationale": "Ecommerce rule does not apply to B2B SaaS.",
                    })
                elif f.finding_id == "det_f_01":
                    items.append({
                        "finding_id": f.finding_id,
                        "verdict": "DOWNGRADED",
                        "adjusted_severity": "LOW",
                        "business_impact_rationale": "Minor hygiene issue with limited ranking impact.",
                    })
                else:
                    items.append({
                        "finding_id": f.finding_id,
                        "verdict": "CONFIRMED",
                        "business_impact_rationale": "Directly affects indexation of commercial page.",
                    })
        return {"verifications": items}

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_generate_structured)

    orch = AnalysisOrchestrator()
    ledger = await orch._verify_deterministic_findings_with_ai(model_router=mock_router, blackboard=bb)

    assert len(batch_calls) == 2  # 15 + 3
    assert ledger["deterministic_findings_total"] == 18
    assert ledger["deterministic_findings_ai_reviewed"] == 18
    assert ledger["false_positive_count"] == 1
    assert ledger["downgraded_count"] == 1
    assert ledger["confirmed_count"] == 16
    assert ledger["ai_review_status"] == "completed"

    # False positive is preserved (not deleted), downgraded to INFO, and held from executive
    f0 = findings[0]
    assert f0.severity == Severity.INFO
    assert f0.held_from_executive is True
    assert f0.evidence_refs == ["ev_pricing_001"]
    assert "[AI Review: FALSE_POSITIVE]" in (f0.verification_notes or "")

    # Downgraded finding reduced from HIGH -> LOW
    assert findings[1].severity == Severity.LOW
    assert findings[2].severity == Severity.HIGH
    assert findings[2].adversarial_reviewed is True


@pytest.mark.asyncio
async def test_batched_critic_audits_100_percent_of_claims():
    bb = _make_blackboard_with_sections_and_findings()
    for i in range(25):
        bb.claim_registry.add_claim(
            Claim(
                id=f"clm_{i:02d}",
                agent_id="seo.html.v3",
                category=Category.ON_PAGE_SEO,
                severity=Severity.MEDIUM,
                statement=f"Observed heading issue #{i} on pricing page",
                evidence_refs=["ev_pricing_001"],
                confidence=0.85,
                verification_status=VerificationStatus.PENDING_VERIFICATION,
            )
        )

    calls = []

    async def _fake_critic_call(**kwargs):
        calls.append(kwargs)
        assert kwargs["model_tier"] == "judge_model"
        prompt = kwargs["task_contract"]
        results = []
        for i in range(25):
            cid = f"clm_{i:02d}"
            if cid in prompt:
                results.append({
                    "claim_id": cid,
                    "decision": "unsupported" if i == 24 else "supported",
                    "rationale": "Checked against ev_pricing_001",
                })
        return {"results": results}

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_critic_call)

    critic = CognitiveCriticWorker("worker_critic", mock_router)
    res = await critic.execute_task("34_adversarial_verification", bb)

    assert len(calls) == 2  # 20 + 5
    assert res["batches_executed"] == 2
    assert res["total_audited"] == 25
    assert len(res["verified_claims"]) == 24
    assert len(res["rejected_claims"]) == 1
    assert res["rejected_claims"][0]["claim_id"] == "clm_24"

    all_claims = {c.id: c for c in bb.claim_registry.get_all()}
    assert all_claims["clm_00"].verification_status == VerificationStatus.VERIFIED
    assert all_claims["clm_24"].verification_status == VerificationStatus.REJECTED


def test_orchestrator_stage_ordering_invariants():
    src = inspect.getsource(AnalysisOrchestrator._execute_analysis_pipeline_scoped)

    idx_budget = src.index("model_router.apply_page_budget(")
    idx_det = src.index("self._run_deterministic_analyzers(")
    idx_biz = src.index("BusinessUnderstandingOrchestrator(model_router)")
    idx_verify = src.index("self._verify_deterministic_findings_with_ai(")
    idx_dag = src.index("agent_pool.execute_all(")
    idx_geo = src.index("evaluate_geo_readiness(")
    idx_sandbox = src.index("DynamicQuestionSandboxEngine(model_router=model_router)")
    idx_copy = src.index("PageIntelligenceAgent(model_router)")
    idx_critic = src.index("worker_critic.execute_task(")
    idx_integrity = src.index("integrity_gate.validate_claims_and_evidence(")
    idx_synth = src.index("worker_synthesizer.execute_task(")

    assert idx_budget < idx_det < idx_biz < idx_verify < idx_dag
    assert idx_dag < idx_geo < idx_sandbox < idx_copy
    assert idx_copy < idx_critic < idx_integrity < idx_synth
