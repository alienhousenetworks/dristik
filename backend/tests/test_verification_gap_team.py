"""
Release-blocking tests for Phase 2 & 3:
- Critical claim suppression (GUESSING+CRITICAL stays held until verified)
- Schema field ingestion (why_it_matters, validation_criteria, confidence_basis)
- No duplicate task_card injection in PromptCompiler + SpecialistAgent
"""
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domain.enums import Category, Materiality, RubricConfidence, Severity
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.orchestration.runtime.registry import SPECIALIST_AGENTS_V3
from app.orchestration.runtime.specialist import SpecialistAgent
from app.orchestration.runtime.task_cards import TASK_CARDS
from app.core.inference.model_router import ModelRouter


def test_guessing_critical_claims_remain_held_after_falsify():
    bb = CognitiveBlackboard(run_id="run_hold_test", website_url="https://example.com")
    claim = bb.claim_registry.register_claim(
        agent_id="content.depth.v3",
        statement="Critical unverified gap",
        category=Category.CONTENT,
        severity=Severity.CRITICAL,
        evidence_refs=[],
        confidence=0.35,
        confidence_rubric=RubricConfidence.GUESSING,
        materiality=Materiality.CRITICAL,
    )
    claim.held_from_executive = True
    adv_agent = SpecialistAgent(SPECIALIST_AGENTS_V3["verification.adversarial.v3"], ModelRouter())
    adv_agent._falsify_unbacked_claims(bb)

    assert claim.held_from_executive is True, "GUESSING+CRITICAL claim must NOT be released before adversarial+critic verification"


def test_ingest_llm_preserves_schema_fields():
    bb = CognitiveBlackboard(run_id="run_ingest_test", website_url="https://example.com")
    ev = bb.evidence_store.add_evidence(
        source_type="dom",
        analyzer="test",
        url="https://example.com",
        selector="h1",
        text="Acme Platform",
    )
    agent = SpecialistAgent(SPECIALIST_AGENTS_V3["business.discovery.v3"], ModelRouter())
    raw = {
        "status": "completed",
        "mode": "OBSERVED",
        "claims": [
            {
                "statement": "Homepage H1 says 'Acme Platform'.",
                "severity": "MEDIUM",
                "confidence": 0.9,
                "evidence_refs": [ev.id],
                "evidence_status": "supported",
                "why_it_matters": "Buyers cannot tell what the platform does in 3 seconds.",
                "validation_criteria": "H1 states product category and target buyer.",
                "confidence_basis": "Directly observed in DOM h1 node.",
                "confidence_rubric": "CERTAIN",
                "materiality": "MAJOR",
                "source_agreement": 2,
                "source_integrity_label": "CORROBORATED",
                "recommendation": "Clarify H1.",
                "impact": 7,
                "effort": 2,
            }
        ],
        "observations": {},
    }
    agent._ingest_llm(bb, raw, [ev])
    claims = bb.claim_registry.get_all()
    assert len(claims) == 1
    c = claims[0]
    assert c.why_it_matters == "Buyers cannot tell what the platform does in 3 seconds."
    assert c.validation_criteria == "H1 states product category and target buyer."
    assert bool(c.confidence_basis)
    assert c.confidence_rubric is not None
    assert c.materiality == Materiality.MAJOR
    assert c.source_agreement >= 1


@pytest.mark.asyncio
async def test_no_duplicate_task_card_in_prompt():
    bb = CognitiveBlackboard(run_id="run_prompt_test", website_url="https://example.com")
    ev = bb.evidence_store.add_evidence(
        source_type="dom",
        analyzer="test",
        url="https://example.com",
        selector="title",
        text="Acme",
    )
    captured = {}

    mock_router = MagicMock(spec=ModelRouter)
    mock_router.client = MagicMock(provider="gemini")

    async def fake_generate_structured(**kwargs):
        captured.update(kwargs)
        return {"status": "completed", "claims": [], "observations": {}}

    mock_router.generate_structured = AsyncMock(side_effect=fake_generate_structured)

    agent = SpecialistAgent(SPECIALIST_AGENTS_V3["business.discovery.v3"], mock_router)
    await agent._llm_audit(bb, [ev])

    card = TASK_CARDS["business.discovery.v3"].strip()
    assert captured["task_card"].strip() == card
    assert card not in captured["task_contract"], "task_card must not be duplicated inside task_contract"


def test_prompt_budget_enforced_with_documented_exceptions():
    from app.orchestration.runtime.task_cards import get_task_card_budget_report
    report = get_task_card_budget_report()
    assert len(report) == 68
    over_budget = [aid for aid, info in report.items() if not info["within_budget"]]
    assert not over_budget, f"Task cards exceeded ceiling: {over_budget}"


def test_business_profile_consistency_via_tool_bus():
    from app.domain.models import BusinessProfile
    from app.orchestration.runtime.tool_bus import AgentToolBus

    bp = BusinessProfile(
        business_name="Acme Corp",
        industry="B2B SaaS",
        niche="Cloud Security",
        personas=["CISO", "VP Engineering"],
        pain_points=["Alert fatigue"],
        competitors=["RivalOne"],
        positioning="Zero-trust cloud posture",
        verified_assumptions=["SOC2 Type II"],
        unverified_assumptions=["Enterprise SLA"],
    )
    bb = CognitiveBlackboard(run_id="run_bp_test", website_url="https://acme.example")
    bb.business_profile = bp
    ctx = AgentToolBus(bb).get_business_context()
    assert ctx["business_profile"]["profile_version"] == bp.profile_version == "4.0"
    assert ctx["business_profile"]["personas"] == ["CISO", "VP Engineering"]
    assert ctx["business_profile"]["competitors"] == ["RivalOne"]


@pytest.mark.asyncio
async def test_failure_isolation_in_agent_pool():
    from app.orchestration.agent_pool import AgentPool
    from app.domain.models import CrawlManifest, PageEvidence

    pool = AgentPool(ModelRouter())
    bb = CognitiveBlackboard(run_id="run_iso_test", website_url="https://example.com")
    bb.pages = [PageEvidence(url="https://example.com/", title="Example", h1=["Example"])]
    bb.crawl_manifest = CrawlManifest(website_url="https://example.com", domain="example.com", pages=bb.pages)

    # Force one deterministic agent to raise
    async def boom(_bb):
        raise RuntimeError("simulated specialist crash")

    pool.agents["seo.crawl.v3"].run = boom
    summary = await pool.execute_all(bb, active_pillars={"seo"})
    assert summary["errors"] >= 1
    assert summary["results"]["seo.crawl.v3"]["status"] == "error"
    assert summary["results"]["seo.html.v3"]["status"] in ("completed", "partial", "unavailable")


@pytest.mark.asyncio
async def test_reproducibility_of_deterministic_specialists():
    from app.domain.models import CrawlManifest, PageEvidence

    def make_bb():
        bb = CognitiveBlackboard(run_id="run_repro", website_url="https://example.com")
        bb.pages = [PageEvidence(url="https://example.com/", title="Hi", h1=[])]
        bb.crawl_manifest = CrawlManifest(website_url="https://example.com", domain="example.com", pages=bb.pages)
        return bb

    agent = SpecialistAgent(SPECIALIST_AGENTS_V3["seo.html.v3"], ModelRouter())
    r1 = await agent.run(make_bb())
    r2 = await agent.run(make_bb())
    s1 = [c["statement"] for c in r1.get("claims", [])]
    s2 = [c["statement"] for c in r2.get("claims", [])]
    assert s1 == s2

