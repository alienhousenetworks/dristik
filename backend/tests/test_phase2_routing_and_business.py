"""Phase 2 tests: Frontier routing, OpenAI provider registration, ₹20–₹30/page dynamic budgets, PromptCompiler limits, and full-site map-reduce Business Understanding."""
import pytest

from app.core.config import Settings, settings
from app.core.inference.budget_manager import BudgetManager
from app.core.inference.model_router import ModelRouter
from app.core.inference.prompt_compiler import PromptCompiler
from app.domain.evidence.models import Evidence
from app.domain.models import PageEvidence, PageSection
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.seo.business.understanding import BusinessUnderstandingOrchestrator


def test_phase2_frontier_defaults_and_openai_provider():
    cfg = Settings(_env_file=None, ANTHROPIC_API_KEY="sk-ant-test")
    anth = cfg.get_llm_credentials("anthropic")
    assert anth["model_reasoning"] == "claude-sonnet-4-6"
    assert anth["model_fast"] == "claude-haiku-4-5-20251001"

    cfg_oai = Settings(_env_file=None, OPENAI_API_KEY="sk-oai-test")
    assert "openai" in cfg_oai.get_configured_providers()
    assert cfg_oai.get_active_provider() == "openai"
    oai = cfg_oai.get_llm_credentials("openai")
    assert oai["model_reasoning"] == "gpt-4.1"
    assert oai["model_fast"] == "gpt-4.1-mini"

    cfg_gem = Settings(_env_file=None, GEMINI_API_KEY="gem-test")
    gem = cfg_gem.get_llm_credentials("gemini")
    assert gem["model_reasoning"] == "gemini-2.5-pro"
    assert gem["model_fast"] == "gemini-2.5-flash"


def test_phase2_dynamic_budget_curve_1_to_200_pages():
    p1 = BudgetManager.compute_audit_budget(1)
    p20 = BudgetManager.compute_audit_budget(20)
    p50 = BudgetManager.compute_audit_budget(50)
    p200 = BudgetManager.compute_audit_budget(200)

    # 1-page gets base overhead so site-level reasoning doesn't starve
    assert p1.max_budget_usd >= 0.70
    # 20 pages ~ ₹25–₹30/page effective
    assert 22.0 <= p20.effective_per_page_inr <= 32.0
    # Volume taper: effective per-page cost drops as pages increase from 1 -> 20 -> 50 -> 200
    assert p1.effective_per_page_usd > p20.effective_per_page_usd > p50.effective_per_page_usd > p200.effective_per_page_usd
    assert p200.max_model_calls >= 400

    # frontier_all boosts budget by 1.45x and sets frontier_copy_page_cap = pages_count
    p200_all = BudgetManager.compute_audit_budget(200, depth_mode="frontier_all")
    assert p200_all.max_budget_usd > p200.max_budget_usd
    assert p200_all.frontier_copy_page_cap == 200


def test_phase2_capability_routing_and_prompt_compiler_slice_expansion(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "AI_DEPTH_MODE", "tiered_frontier")

    router = ModelRouter()
    assert router._select_model("business_discovery") == "claude-sonnet-4-6"
    assert router._select_model("seo_verification") == "claude-sonnet-4-6"
    assert router._select_model("cro_analysis") == "claude-sonnet-4-6"
    assert router._select_model("remediation_synthesis") == "claude-sonnet-4-6"
    assert router._select_model("page_section_digest") == "claude-haiku-4-5-20251001"

    monkeypatch.setattr(settings, "AI_DEPTH_MODE", "frontier_all")
    assert router._select_model("page_section_digest") == "claude-sonnet-4-6"

    # PromptCompiler no longer clips at 200 chars
    long_text = "A" * 900
    ev = Evidence(
        id="ev_001",
        source_type="page_section",
        analyzer="section_extractor",
        url="https://example.com/",
        selector="section#hero",
        text=long_text,
        hash="a" * 64,
    )
    formatted = PromptCompiler().format_evidence_slice(ev)
    assert long_text in formatted


@pytest.mark.asyncio
async def test_phase2_business_understanding_full_site_map_reduce():
    calls = []

    class _FakeRouter:
        async def generate_structured(self, **kwargs):
            calls.append(kwargs)
            cap = kwargs.get("capability")
            if cap == "page_section_digest":
                return {
                    "offerings": ["Postgres Backups"],
                    "audience_signals": ["DevOps Teams"],
                    "pricing_or_proof_signals": ["$49/mo"],
                    "urls_covered": [p["url"] for p in kwargs["site_facts"]["batch_pages"]],
                }
            if cap == "business_discovery":
                return {
                    "business_name": "Acme Cloud",
                    "industry": "Cloud Infrastructure",
                    "sub_industry": "Database Backup",
                    "what_company_does": "Automates Postgres backups",
                    "who_it_serves": ["DevOps Engineers"],
                    "what_it_sells": ["Backup Platform"],
                    "how_it_makes_money": "SaaS subscription",
                    "confidence": 0.92,
                }
            if cap == "intent_journey":
                return {"primary_intent": "saas", "secondary_intents": [], "journey_stages": ["Trial"], "conversion_events": ["Sign up"], "friction_points": [], "confidence": 0.9}
            if cap == "category_product":
                return {"product_categories": ["Backup"], "services": [], "service_categories": [], "product_families": ["Acme DB"], "use_cases": ["Disaster Recovery"], "audience_segments": ["SREs"], "confidence": 0.9}
            if cap == "business_model":
                return {"primary_model": "B2B SaaS", "secondary_model": None, "commercial_motion": "self-serve", "conversion_model": "free trial", "confidence": 0.9}
            return {
                "intent_alignment_analysis": "Aligned",
                "architecture_supports_goal": True,
                "value_proposition_clarity": "Clear",
                "machine_comprehension_assessment": "Strong",
                "contradictions_detected": [],
                "content_gaps": [],
                "strategic_hypotheses": [],
                "confidence": 0.9,
            }

    bb = CognitiveBlackboard(run_id="run_p2_biz", website_url="https://acmecloud.io")
    # Create 20 pages (>15 triggers map-reduce overflow digestion)
    bb.pages = [
        PageEvidence(
            url=f"https://acmecloud.io/page-{i}",
            page_type="homepage" if i == 0 else ("pricing" if i == 1 else "product"),
            title=f"Acme Page {i}",
            h1=[f"Heading {i}"],
            sections=[
                PageSection(
                    section_id="sec_01_hero",
                    section_role="hero",
                    heading_text=f"Heading {i}",
                    body_text=f"Detailed section content for page {i}.",
                    word_count=6,
                )
            ],
        )
        for i in range(20)
    ]

    orch = BusinessUnderstandingOrchestrator(_FakeRouter())
    rep = await orch.execute_business_understanding(bb)
    assert rep.industry == "Cloud Infrastructure"
    assert bb.blackboard_state["full_site_dossier"]["total_pages_analyzed"] == 20
    assert len(bb.blackboard_state["full_site_dossier"]["overflow_pages_digests"]) == 1

    # Verify all 5 core agents ran with model_tier="reasoning_model" and map phase ran on fast_slm
    tiers_by_cap = {c["capability"]: c.get("model_tier") for c in calls}
    assert tiers_by_cap["page_section_digest"] == "fast_slm"
    for core_cap in ("business_discovery", "intent_journey", "category_product", "business_model", "semantic_strategist"):
        assert tiers_by_cap[core_cap] == "reasoning_model"
