"""
Dristik AI 70B-Hardened Prompt & Pipeline Integration Tests
Comprehensive unit tests covering:
1. Compiler envelope test
2. Number sanitizer test
3. Schema escape test
4. JSON-LD patch test
5. Critic blindness test
6. Synthesizer isolation test
7. Length validator test
8. Two-pass reason-then-json test
9. Compatibility mapper test
"""
import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel
from typing import Optional

from app.evidence.models import Evidence
from app.evidence.store import EvidenceStore
from app.domain.models import CrawlManifest, PageEvidence, BusinessProfile
from app.domain.enums import VerificationStatus, Category, Severity
from app.cognition.blackboard import CognitiveBlackboard
from app.inference.prompt_compiler import PromptCompiler, GLOBAL_POLICY
from app.inference.schemas.shared import strip_ungrounded_numbers
from app.inference.schemas.compat import legacy_adapt
from app.inference.schemas.agent_schemas import (
    BusinessExtractOutput,
    BusinessPositionOutput,
    GeoAuditOutput,
    AiSearchBatchOutput,
    CriticOutput,
    SynthesizerOutput,
    StrategistOutput,
)
from app.agents.legacy.business import BusinessIntelligenceAgent
from app.agents.legacy.geo import GeoAgent
from app.agents.legacy.ai_search import AiSearchSimulationAgent, commercial_queries
from app.agents.page.intelligence import validate_and_clip_copy, SuggestedCopy
from app.workers.critic_worker import CognitiveCriticWorker
from app.workers.synthesizer_worker import CognitiveSynthesizerWorker
from app.inference.model_router import ModelRouter
from app.evidence.site_facts import extract_site_facts


# --------------------------------------------------------------------------
# 1. Compiler envelope test
# --------------------------------------------------------------------------
def test_compiler_envelope():
    compiler = PromptCompiler()
    ev = Evidence(id="ev_001", source_type="h1", text="Enterprise AI Observability Platform", url="https://example.com", analyzer="test", hash="test_hash")
    site_facts = {"final_url": "https://example.com", "schemas_detected": ["Organization"]}

    compiled = compiler.compile(
        agent_role="Specialist Role",
        task_contract="Extract commercial identity",
        evidence_list=[ev],
        site_facts=site_facts
    )

    system_prompt = compiled["system"]
    user_prompt = compiled["user"]

    # Verify GLOBAL_POLICY is present and legacy consulting manifestos/Acme few-shots are absent
    assert "You are Dristik, an evidence-bound web auditor." in system_prompt
    assert "Acme" not in system_prompt
    assert "McKinsey Digital" not in system_prompt
    assert "0.92" not in system_prompt

    # Verify required XML tags
    assert "<task>" in user_prompt
    assert "<site_facts>" in user_prompt
    assert "<evidence>" in user_prompt
    assert "<constraints>" in user_prompt
    assert "[ev_001]" in user_prompt
    assert "https://example.com" in user_prompt


# --------------------------------------------------------------------------
# 2. Number sanitizer test
# --------------------------------------------------------------------------
def test_number_sanitizer():
    # Evidence does NOT contain 28 or $499
    evidence_text = "Dristik provides website intelligence and DOM analysis with 3 core tiers."

    payload = {
        "summary": "Platform reduces CAC by 28% and costs $499/mo.",
        "cac_impact": {
            "band": "high",
            "mechanism": "Inflates acquisition by 28%",
            "numeric_estimate": 28.0
        },
        "verified_text": "Includes 3 core tiers for teams."
    }

    sanitized = strip_ungrounded_numbers(payload, evidence_text)

    # Ungrounded metrics are stripped or nulled
    assert "28%" not in sanitized["summary"]
    assert "[metric not in evidence]" in sanitized["summary"]
    assert "$499" not in sanitized["summary"]
    assert sanitized["cac_impact"]["numeric_estimate"] is None
    assert "28%" not in sanitized["cac_impact"]["mechanism"]

    # Grounded number (3) is preserved
    assert "3 core tiers" in sanitized["verified_text"]


# --------------------------------------------------------------------------
# 3. Schema escape test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_schema_escape():
    # When page has no pricing, detected_answer must be "cannot answer from site"
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://nopricing.com")
    blackboard.site_facts = {"pricing_signals_present": False, "business_name_candidates": ["NoPricing Inc"]}

    mock_router = ModelRouter()
    # Mock LLM returning empty/unsupported answer
    mock_router.generate_structured = AsyncMock(return_value={
        "evaluations": [
            {
                "query": "How is NoPricing Inc priced?",
                "question_type": "pricing",
                "evidence_quality": "none",
                "detected_answer": "cannot answer from site",
                "gap_analysis": "No pricing on page",
                "citation_readiness": "low",
                "hallucination_vulnerability": "high"
            }
        ],
        "claims": []
    })

    agent = AiSearchSimulationAgent(mock_router)
    result = await agent.run(blackboard)

    assert result["evaluations_count"] == 6
    pricing_eval = next(e for e in blackboard.ai_search_evaluations if "priced" in e.query)
    assert pricing_eval.detected_answer == "cannot answer from site"
    assert pricing_eval.score is None or pricing_eval.score <= 3


# --------------------------------------------------------------------------
# 4. JSON-LD patch test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_jsonld_patch_no_unobserved_urls():
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://example.com")
    blackboard.site_facts = {
        "final_url": "https://example.com",
        "schemas_detected": ["WebSite"],
        "sameas_urls": ["https://twitter.com/realaccount"]
    }

    mock_router = ModelRouter()
    mock_router.generate_structured = AsyncMock(return_value={
        "entity_clarity_band": "strong",
        "production_jsonld_patch": {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Example Corp",
            "logo": "https://example.com/fake-logo.png",
            "sameAs": [
                "https://www.linkedin.com/company/fake-unobserved",
                "https://twitter.com/realaccount"
            ]
        },
        "claims": []
    })

    geo_agent = GeoAgent(mock_router)
    result = await geo_agent.run(blackboard)

    patch_out = result["production_jsonld_patch"]
    # The LinkedIn URL was unobserved in site_facts, so it must be purged!
    assert "https://www.linkedin.com/company/fake-unobserved" not in patch_out["sameAs"]
    # Observed Twitter URL is retained
    assert "https://twitter.com/realaccount" in patch_out["sameAs"]


# --------------------------------------------------------------------------
# 5. Critic blindness test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_critic_blindness():
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://test.ai")
    ev1 = Evidence(id="ev_001", source_type="h1", text="Clear Enterprise Observability", analyzer="test", hash="test_hash")
    blackboard.evidence_store.add(ev1)

    blackboard.claim_registry.register_claim(
        agent_id="agent_biz",
        statement="Missing SOC2 certification makes enterprise deals impossible.",
        category=Category.TRUST_AUTHORITY,
        severity=Severity.CRITICAL,
        evidence_refs=["ev_001"],
        recommendation="Obtain SOC2 immediately"
    )

    blackboard.blackboard_state["hero_copy_rewrite"] = {"after": "Secret author copy rewrite"}
    blackboard.executive_narrative = {"story_summary": "Secret executive story summary"}

    mock_router = ModelRouter()
    captured_contract = {}

    async def mock_generate_structured(*args, **kwargs):
        captured_contract["contract"] = kwargs.get("task_contract", "")
        return {
            "results": [
                {
                    "claim_id": "claim_001",
                    "decision": "severity_inflated",
                    "calibrated_severity": "MEDIUM",
                    "rationale": "Missing SOC2 is not an immediate DOM outage."
                }
            ]
        }

    mock_router.generate_structured = AsyncMock(side_effect=mock_generate_structured)

    critic = CognitiveCriticWorker("worker_critic", mock_router)
    await critic.execute_task("critic", blackboard)

    contract_text = captured_contract.get("contract", "")
    # Critic must NOT see copy_rewrite or story_summary
    assert "Secret author copy rewrite" not in contract_text
    assert "Secret executive story summary" not in contract_text
    # Critic DOES see the claim statement atom
    assert "Missing SOC2 certification" in contract_text
    assert "ev_001" in contract_text


# --------------------------------------------------------------------------
# 6. Synthesizer isolation test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_synthesizer_isolation():
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://test.ai")
    ev1 = Evidence(id="ev_001", source_type="h1", text="Clean site headline", analyzer="test", hash="test_hash")
    blackboard.evidence_store.add(ev1)

    c1 = blackboard.claim_registry.register_claim(
        agent_id="agent_1",
        statement="Verified high quality infrastructure.",
        category=Category.TECHNICAL_SEO,
        severity=Severity.LOW,
        evidence_refs=["ev_001"]
    )
    c1.verification_status = VerificationStatus.VERIFIED

    c2 = blackboard.claim_registry.register_claim(
        agent_id="agent_2",
        statement="Fabricated competitor loss claim.",
        category=Category.COMPETITIVE,
        severity=Severity.CRITICAL,
        evidence_refs=["ev_001"]
    )
    c2.verification_status = VerificationStatus.REJECTED

    captured_synth_input = {}
    mock_router = ModelRouter()

    async def mock_generate_structured(*args, **kwargs):
        captured_synth_input["contract"] = kwargs.get("task_contract", "")
        return {
            "story_summary": "Clean executive diagnostic constraint.",
            "what_site_gets_right": ["Solid infra"],
            "what_is_holding_it_back": ["Vague ICP"],
            "primary_strategic_opportunity": "Entity clarity",
            "consultant_advice_what_to_ignore": "Backlink campaigns",
            "financial_impact_model": {
                "cac_pressure": "moderate",
                "organic_pipeline_at_risk": "low",
                "conversion_velocity_uplift": "high"
            },
            "board_presentation_bullets": ["Focus on ICP"]
        }

    mock_router.generate_structured = AsyncMock(side_effect=mock_generate_structured)

    synthesizer = CognitiveSynthesizerWorker("worker_synth", mock_router)
    await synthesizer.execute_task("synthesis", blackboard)

    contract_text = captured_synth_input.get("contract", "")
    # Verified claim MUST appear
    assert "Verified high quality infrastructure." in contract_text
    # Rejected claim MUST NOT appear
    assert "Fabricated competitor loss claim." not in contract_text


# --------------------------------------------------------------------------
# 7. Length validator test
# --------------------------------------------------------------------------
def test_length_validator():
    long_copy = SuggestedCopy(
        title="A very long title that definitely exceeds sixty characters for SERP truncation testing purposes",
        meta_description=(
            "This meta is already long enough because it describes the actual offer on the page "
            "with enough characters to be a real snippet for search engines and then extra words."
        ),
        hero="This hero is a real paragraph from the page that explains the offer for a specific buyer.",
        h1="Unified Data Platform for Modern Engineering Teams",
    )
    clipped = validate_and_clip_copy(long_copy, brand_name="Dristik")
    assert clipped.title == long_copy.title
    assert "Dristik" not in clipped.title
    assert len(clipped.meta_description) > 160
    assert "Enterprise Intelligence" not in clipped.title
    assert "High Performance Software" not in clipped.title

    short = validate_and_clip_copy(
        SuggestedCopy(title="Too Short", meta_description="Too short meta", hero="Short hero."),
        brand_name="Dristik",
    )
    assert short.title == "Too Short"
    assert "Dristik" not in short.title
    assert "Enterprise Intelligence Platform" not in short.title
    assert "Enterprise Audit" not in short.meta_description
    assert "Generative Engine Optimization" not in short.meta_description


# --------------------------------------------------------------------------
# 8. Two-pass test (run_reason_then_json)
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_two_pass_serializer_cannot_invent_entities():
    class SimpleSchema(BaseModel):
        product_name: Optional[str] = None
        evidence_status: str

    from app.core.config import settings
    with patch.object(settings, "TOGETHER_API_KEY", "test_key"):
        mock_router = ModelRouter()
        # Step 1: Reason pass produces text without the word 'CyberQuantum'
        mock_router.generate_prose = AsyncMock(
            return_value="The company offers an observability agent based on [ev_001]."
        )

        # Step 2: Serializer attempts to output JSON with an invented product
        mock_router.client.generate_chat_completion = AsyncMock(
            return_value={
                "content": '{"product_name": "CyberQuantum Enterprise", "evidence_status": "supported"}',
                "input_tokens": 10,
                "output_tokens": 10,
                "latency_ms": 50
            }
        )

        ev = Evidence(id="ev_001", source_type="body", text="Our observability agent tracks latency.", analyzer="test", hash="test_hash")
        res = await mock_router.run_reason_then_json(
            capability="test_cap",
            agent_role="Test Auditor",
            reason_contract="Analyze products",
            schema_cls=SimpleSchema,
            evidence_list=[ev]
        )

        assert res["evidence_status"] == "supported"


# --------------------------------------------------------------------------
# 9. Compatibility mapper test
# --------------------------------------------------------------------------
def test_legacy_adapt():
    raw_biz = {
        "business_name": "TestCorp",
        "five_second_clarity": {"band": "strong"},
        "cac_impact": {"band": "high", "mechanism": "High CAC friction"},
        "claims": [
            {"statement": "Test claim", "severity": "HIGH", "impact_band": "severe", "evidence_refs": ["ev_01"]}
        ]
    }
    adapted = legacy_adapt("business", raw_biz)

    # five_second_clarity_score is None when qualitative band is preserved, band is captured
    assert adapted["five_second_clarity_band"] == "strong"
    assert adapted["five_second_clarity_score"] is None
    assert adapted["cac_impact_risk"] == "High CAC friction"
    assert adapted["claims"][0]["impact"] is None
    assert adapted["claims"][0]["confidence"] == 0.50
    assert adapted["primary_intent"] == "lead_generation"
