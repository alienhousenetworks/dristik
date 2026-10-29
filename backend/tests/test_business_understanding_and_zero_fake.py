"""
Tests for Dristik AI Advanced Business Understanding & Zero-Fake Data Architecture:
1. Five cognitive workers & SemanticBusinessRepresentation assembly
2. Multi-agent consensus calculation
3. Contradiction detection engine (User-declared SaaS vs agency evidence)
4. Offline structural fallback
5. Zero-fake Google Search Console guarantee (UNAVAILABLE state when unauthenticated)
"""
import pytest
from unittest.mock import AsyncMock
from app.domain.models import PageEvidence, FindingEvidence
from app.domain.enums import EvidenceState
from app.cognition.blackboard import CognitiveBlackboard
from app.intelligence.business.understanding import BusinessUnderstandingOrchestrator
from app.intelligence.business.search_console import search_console_engine
from app.inference.model_router import ModelRouter
from app.inference.telemetry import TelemetryTracker
from app.inference.schemas import (
    AgentDiscoveryOutput,
    AgentIntentJourneyOutput,
    AgentCategoryProductOutput,
    AgentBusinessModelOutput,
    AgentSemanticStrategistOutput
)


@pytest.mark.asyncio
async def test_business_understanding_orchestrator_multi_agent_flow():
    """Verify that all 5 cognitive workers execute and assemble into a unified SemanticBusinessRepresentation."""
    blackboard = CognitiveBlackboard(run_id="run_test_biz_multi", website_url="https://cloudscale.io")
    blackboard.pages = [
        PageEvidence(
            url="https://cloudscale.io",
            title="CloudScale | Automated Cloud Cost Optimization for Kubernetes",
            h1=["Cut Kubernetes Cloud Spend by 40% Autonomously"],
            ctas=["Start Free Trial", "Schedule Architecture Review"],
            internal_links=["/pricing", "/docs", "/integrations", "/contact"],
            word_count=1400
        )
    ]
    blackboard.site_facts = {
        "business_name_candidates": ["CloudScale"],
        "industry": "B2B SaaS / Cloud Infrastructure",
    }

    router = ModelRouter(telemetry_tracker=TelemetryTracker())

    # Mock the 5 agent outputs
    async def mock_generate_structured(capability, *args, **kwargs):
        if capability == "business_discovery":
            return AgentDiscoveryOutput(
                business_name="CloudScale",
                industry="Cloud Infrastructure Software",
                sub_industry="FinOps & Cost Management",
                what_company_does="Autonomous Kubernetes infrastructure cost optimization platform",
                who_it_serves=["Platform Engineers", "DevOps Leaders", "CTOs"],
                what_it_sells=["CloudScale Autonomous SaaS Engine", "Enterprise Kubernetes Connector"],
                how_it_makes_money="Subscription-based tiered SaaS pricing based on cluster nodes",
                core_problem_solved="Eliminating runaway cloud spend and over-provisioned clusters",
                primary_business_objective="Self-serve product trial on-ramps and enterprise demo requests",
                confidence=0.94,
                evidence_excerpts=["Cut Kubernetes Cloud Spend by 40% Autonomously"]
            ).model_dump()
        elif capability == "intent_journey":
            return AgentIntentJourneyOutput(
                primary_intent="saas",
                secondary_intents=["product_discovery", "lead_generation"],
                journey_stages=["Discovery", "ROI Education", "Architecture Trust", "14-Day Free Trial"],
                conversion_events=["Start Free Trial", "Schedule Demo"],
                friction_points=["Pricing tier thresholds require clearer node definitions"],
                confidence=0.92,
                evidence_excerpts=["Start Free Trial"]
            ).model_dump()
        elif capability == "category_product":
            return AgentCategoryProductOutput(
                product_categories=["Kubernetes FinOps Software", "Infrastructure Automation"],
                product_families=["CloudScale Enterprise", "CloudScale Cloud Agent"],
                services=["Dedicated Onboarding Advisory"],
                use_cases=["EKS Cost Reduction", "GKE Right-sizing"],
                audience_segments=["Scale-up & Enterprise Engineering Teams"],
                confidence=0.91,
                evidence_excerpts=["CloudScale Autonomous SaaS Engine"]
            ).model_dump()
        elif capability == "business_model":
            return AgentBusinessModelOutput(
                primary_model="B2B SaaS",
                secondary_model="Enterprise Sales",
                commercial_motion="hybrid",
                conversion_model="Credit card self-serve trial + Enterprise Annual Contracts",
                confidence=0.93,
                reasoning="Self-serve signup accompanied by enterprise custom quotation tiers",
                evidence_excerpts=["Start Free Trial", "Schedule Architecture Review"]
            ).model_dump()
        elif capability == "semantic_strategist":
            return AgentSemanticStrategistOutput(
                intent_alignment_analysis="Website architecture strongly supports trial conversions with clear CTA hierarchy.",
                architecture_supports_goal=True,
                value_proposition_clarity="Excellent 5-second clarity on hero headline and quantified financial metric.",
                machine_comprehension_assessment="High entity clarity for FinOps SaaS search and citation engines.",
                contradictions_detected=[],
                content_gaps=["Interactive node-count cost calculator"],
                strategic_hypotheses=["Adding direct AWS/GCP Marketplace listing links will accelerate enterprise procurement."],
                confidence=0.95,
                evidence_excerpts=["Cut Kubernetes Cloud Spend by 40% Autonomously"]
            ).model_dump()
        return {}

    router.generate_structured = AsyncMock(side_effect=mock_generate_structured)
    orchestrator = BusinessUnderstandingOrchestrator(model_router=router)

    semantic_rep = await orchestrator.execute_business_understanding(blackboard)

    assert semantic_rep is not None
    assert semantic_rep.business_model == "B2B SaaS"
    assert semantic_rep.website_type == "B2B SaaS"
    assert semantic_rep.primary_intent == "saas"
    assert semantic_rep.confidence >= 0.90
    assert len(semantic_rep.journey_stages) == 4
    assert "Start Free Trial" in semantic_rep.conversion_events
    assert len(semantic_rep.evidence) > 0
    assert semantic_rep.is_disputed is False
    assert "Multi-Agent Consensus" in (semantic_rep.consensus_summary or "")


@pytest.mark.asyncio
async def test_strategist_json_failure_keeps_identity_from_other_agents():
    """A Semantic Strategist JSON miss must not wipe Discovery/Intent/Commercial identity."""
    blackboard = CognitiveBlackboard(run_id="run_test_biz_partial", website_url="https://cloudscale.io")
    blackboard.pages = [
        PageEvidence(
            url="https://cloudscale.io",
            title="CloudScale | Automated Cloud Cost Optimization for Kubernetes",
            h1=["Cut Kubernetes Cloud Spend by 40% Autonomously"],
            ctas=["Start Free Trial"],
            internal_links=["/pricing"],
            word_count=1400
        )
    ]
    blackboard.site_facts = {
        "business_name_candidates": ["CloudScale"],
        "industry": "B2B SaaS / Cloud Infrastructure",
    }

    router = ModelRouter(telemetry_tracker=TelemetryTracker())

    async def mock_generate_structured(capability, *args, **kwargs):
        if capability == "business_discovery":
            return AgentDiscoveryOutput(
                business_name="CloudScale",
                industry="Cloud Infrastructure Software",
                who_it_serves=["Platform Engineers"],
                what_it_sells=["CloudScale Autonomous SaaS Engine"],
                confidence=0.94,
                evidence_excerpts=["Cut Kubernetes Cloud Spend by 40% Autonomously"]
            ).model_dump()
        if capability == "intent_journey":
            return AgentIntentJourneyOutput(
                primary_intent="saas",
                journey_stages=["Discovery", "Trial"],
                conversion_events=["Start Free Trial"],
                confidence=0.92,
            ).model_dump()
        if capability == "category_product":
            return AgentCategoryProductOutput(
                product_categories=["Kubernetes FinOps Software"],
                confidence=0.91,
            ).model_dump()
        if capability == "business_model":
            return AgentBusinessModelOutput(
                primary_model="B2B SaaS",
                commercial_motion="hybrid",
                confidence=0.93,
            ).model_dump()
        if capability == "semantic_strategist":
            return {
                "status": "unavailable",
                "unavailable_reason": "llm_exhausted:Could not parse valid JSON from anthropic response for capability 'semantic_strategist'.",
                "claims": [],
            }
        return {}

    router.generate_structured = AsyncMock(side_effect=mock_generate_structured)
    orchestrator = BusinessUnderstandingOrchestrator(model_router=router)

    semantic_rep = await orchestrator.execute_business_understanding(blackboard)

    assert semantic_rep.llm_status == "ok"
    assert semantic_rep.industry == "Cloud Infrastructure Software"
    assert semantic_rep.business_model == "B2B SaaS"
    assert semantic_rep.website_type == "B2B SaaS"
    assert semantic_rep.primary_intent == "saas"
    assert semantic_rep.journey_stages == ["Discovery", "Trial"]
    assert blackboard.business_profile.business_name == "CloudScale"


@pytest.mark.asyncio
async def test_business_understanding_offline_fallback():
    """Verify that offline structural fallback correctly derives representation from DOM without network calls."""
    blackboard = CognitiveBlackboard(run_id="run_test_fallback", website_url="https://agency-fallback.com")
    blackboard.pages = [
        PageEvidence(
            url="https://agency-fallback.com",
            title="Strategic Digital Agency | Advisory & Engineering",
            h1=["Digital Transformation & Advisory for Modern Enterprises"],
            ctas=["Request Consultation", "View Case Studies"],
            internal_links=["/services", "/case-studies", "/contact"],
            word_count=900
        )
    ]
    blackboard.site_facts = {
        "business_name_candidates": ["Strategic Digital Agency"],
        "industry": "Digital Agency & Design Strategy",
    }

    router = ModelRouter(telemetry_tracker=TelemetryTracker())
    orchestrator = BusinessUnderstandingOrchestrator(model_router=router)

    fallback_rep = orchestrator._build_offline_fallback(blackboard, blackboard.site_facts, [])

    assert fallback_rep is not None
    assert "Professional Services" in fallback_rep.business_model or "Agency" in fallback_rep.business_model
    assert fallback_rep.confidence >= 0.75
    assert len(fallback_rep.evidence) > 0
    assert fallback_rep.evidence[0].state == EvidenceState.OBSERVED
    assert blackboard.business_profile.business_name == "Strategic Digital Agency"


@pytest.mark.asyncio
async def test_contradiction_detection_user_declared_saas_vs_agency_evidence():
    """Verify that declaring SaaS for an agency triggers an explicit ContradictionReport with high confidence."""
    blackboard = CognitiveBlackboard(run_id="run_test_contra", website_url="https://consulting-pro.com")
    blackboard.user_declared_site_type = "saas"
    blackboard.pages = [
        PageEvidence(
            url="https://consulting-pro.com",
            title="Consulting Pro | Management Strategy & Digital Transformation Retainers",
            h1=["Bespoke Advisory Services for Global Enterprises"],
            ctas=["Book a Consultation", "Contact Our Partners"],
            internal_links=["/services", "/about", "/consultants", "/contact-us"],
            word_count=1200
        )
    ]
    blackboard.site_facts = {
        "business_name_candidates": ["Consulting Pro"],
        "industry": "Management Consulting",
    }

    router = ModelRouter(telemetry_tracker=TelemetryTracker())
    orchestrator = BusinessUnderstandingOrchestrator(model_router=router)

    discovery = AgentDiscoveryOutput(
        business_name="Consulting Pro",
        industry="Management Consulting",
        what_company_does="Enterprise advisory and digital transformation retainers",
        who_it_serves=["Fortune 500 Leaders"],
        confidence=0.92,
        evidence_excerpts=["Bespoke Advisory Services for Global Enterprises"]
    )
    commercial = AgentBusinessModelOutput(
        primary_model="Professional Services / Consulting",
        commercial_motion="sales_assisted",
        confidence=0.90,
        evidence_excerpts=["Book a Consultation", "Custom Advisory Retainers"]
    )
    intent = AgentIntentJourneyOutput(
        primary_intent="lead_generation",
        journey_stages=["Discovery", "Education", "Consultation Booking"],
        confidence=0.88
    )
    category = AgentCategoryProductOutput(
        services=["Digital Transformation Advisory", "Strategy Consulting"],
        confidence=0.91
    )
    strategist = AgentSemanticStrategistOutput(
        intent_alignment_analysis="Site operates as consultative service with no software signup.",
        confidence=0.92
    )

    contra = orchestrator._detect_contradictions(
        user_declared="saas",
        user_notes=None,
        discovery=discovery,
        commercial=commercial,
        intent=intent,
        strategist=strategist,
        blackboard=blackboard
    )

    assert contra is not None
    assert contra.contradiction_type == "user_vs_evidence"
    assert "SaaS" in contra.declared_type
    assert "Professional Services" in contra.detected_type
    assert contra.confidence >= 0.85
    assert "User declared website type as" in contra.reason
    assert len(contra.evidence) > 0


def test_zero_fake_search_console_data():
    """Verify that when unauthenticated, Google Search Console returns strictly zero fabricated metrics with UNAVAILABLE status."""
    report = search_console_engine.generate_search_attribution(domain="unconnected-test.com")

    assert report.is_connected is False
    assert report.status == "unavailable"
    assert report.reason == "not_connected"
    assert report.total_monthly_clicks == 0
    assert report.total_monthly_impressions == 0
    assert report.average_ctr == 0.0
    assert report.average_position == 0.0
    assert len(report.top_ranking_keywords) == 0
    assert len(report.competitor_keyword_gaps) == 0
    assert report.provenance.get("status") == "unavailable"
    assert report.provenance.get("reason") == "not_connected"
    assert "Google Search Console is not connected" in report.connection_status_message


def test_robust_business_schemas_handle_null_and_none_elements():
    """Verify that AgentIntentJourneyOutput and related schemas gracefully handle [None], [null], None without validation errors."""
    # Simulates LLM returning [null] or None inside list fields
    raw_payload = {
        "primary_intent": "saas",
        "conversion_events": [None],
        "evidence_excerpts": [None, "https://cloudscale.io/pricing", "null", "  "],
        "journey_stages": None,
        "entry_points": "single_entry",
    }
    
    intent = AgentIntentJourneyOutput.model_validate(raw_payload)
    assert intent.conversion_events == []
    assert intent.evidence_excerpts == ["https://cloudscale.io/pricing"]
    assert intent.journey_stages == []
    assert intent.entry_points == ["single_entry"]

    discovery = AgentDiscoveryOutput.model_validate({
        "who_it_serves": [None],
        "what_it_sells": ["None", "null", "Kubernetes Engine"],
        "evidence_excerpts": None,
    })
    assert discovery.who_it_serves == []
    assert discovery.what_it_sells == ["Kubernetes Engine"]
    assert discovery.evidence_excerpts == []

