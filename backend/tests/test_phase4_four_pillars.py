"""Phase 4 tests: Four Intelligence Engines — AEO Hybrid RAG + Frontier 100-Q,
CRO Frontier AI specialists, GEO AI Citation-Readiness, and SEO Enterprise AI Runner.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.crawl.knowledge.grounded_simulator import GroundedAnswerSimulator
from app.crawl.knowledge.primitives import QuestionBudgetTier
from app.crawl.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph
from app.crawl.retrieval.hybrid_retriever import HybridRetriever, QueryPlanner
from app.crawl.vector_store import VectorStore
from app.cro.agents import (
    CroConversionAgent,
    FormAbandonmentAgent,
    PricingTrustAgent,
    VisualUxFrictionAgent,
)
from app.domain.evidence.models import Evidence
from app.domain.models import BusinessProfile, PageEvidence, PageSection, ResolvedEntity
from app.geo.dynamic_sandbox import DynamicQuestionSandboxEngine
from app.geo.readiness import enrich_geo_readiness_citations, evaluate_geo_readiness
from app.orchestration.cognition.blackboard import CognitiveBlackboard
from app.seo.enterprise.ai_runtime import ModelNotRun, build_model_router_runner


def _sample_d2c_pages():
    return [
        PageEvidence(
            url="https://brightsmile.shop/",
            title="BrightSmile | Nano-Hydroxyapatite Oral Care",
            h1=["Enamel-Safe Daily Oral Care"],
            h2=["Clinically Formulated Toothpaste", "Frequently Asked Questions"],
            word_count=480,
            status_code=200,
            viewport_meta="width=device-width, initial-scale=1",
            ctas=["Shop Starter Kit", "Explore Ingredients"],
            body_text=(
                "BrightSmile creates enamel-safe nano-hydroxyapatite toothpaste and sonic toothbrushes. "
                "Free shipping across India on orders above Rs 499. 30-day money-back guarantee."
            ),
            sections=[
                PageSection(
                    section_id="sec_hero",
                    order=0,
                    section_role="hero",
                    heading_text="Enamel-Safe Daily Oral Care",
                    heading_level="h1",
                    body_text="BrightSmile creates enamel-safe nano-hydroxyapatite toothpaste for sensitive teeth.",
                    word_count=10,
                    ctas=["Shop Starter Kit"],
                ),
                PageSection(
                    section_id="sec_shipping",
                    order=1,
                    section_role="faq",
                    heading_text="Shipping & Returns",
                    heading_level="h2",
                    body_text="Free shipping across India on orders above Rs 499 with a 30-day money-back guarantee.",
                    word_count=15,
                ),
            ],
        ),
        PageEvidence(
            url="https://brightsmile.shop/products/toothpaste",
            title="Nano-HA Toothpaste — BrightSmile",
            h1=["Nano-Hydroxyapatite Toothpaste"],
            word_count=320,
            status_code=200,
            ctas=["Add to Cart"],
            body_text="Price Rs 349. Fluoride-free, SLS-free, safe for daily brushing twice a day.",
            sections=[
                PageSection(
                    section_id="sec_prod",
                    order=0,
                    section_role="product",
                    heading_text="Nano-Hydroxyapatite Toothpaste",
                    heading_level="h1",
                    body_text="Price Rs 349. Fluoride-free, SLS-free, safe for daily brushing twice a day.",
                    word_count=12,
                    ctas=["Add to Cart"],
                ),
            ],
        ),
    ]


def test_hybrid_retriever_fuses_dense_vector_store_and_sections(tmp_path):
    pages = _sample_d2c_pages()
    kg = WebsiteKnowledgeGraph(brand="BrightSmile", domain="brightsmile.shop")
    kg.build_from_pages(pages)

    vs = VectorStore(db_path=str(tmp_path / "vec.db"))
    vs.save_chunks(
        domain="brightsmile.shop",
        url="https://brightsmile.shop/products/toothpaste",
        page_type="product",
        chunks=["Remineralizing calcium apatite gel for sensitive enamel costs Rs 349."],
        vectors=[[1.0, 0.0, 0.0, 0.0]],
        chunk_metadata=[{"section_id": "sec_prod", "section_heading": "Active Formulation"}],
    )

    class _FakeEmbedder:
        def embed_query(self, q: str):
            return [1.0, 0.0, 0.0, 0.0]

    retriever = HybridRetriever(
        graph=kg,
        vector_store=vs,
        embedding_service=_FakeEmbedder(),
        domain="brightsmile.shop",
        pages=pages,
    )
    # Query uses synonym "remineralizing" present only in the dense vector chunk
    plan = QueryPlanner.plan("Does BrightSmile use remineralizing gel?")
    hits = retriever.retrieve("Does BrightSmile use remineralizing gel?", plan)
    assert len(hits) >= 1
    assert any(h.dense_score >= 0.99 for h in hits)
    assert any("https://brightsmile.shop/products/toothpaste" == (h.claim.evidence.url if h.claim.evidence else "") for h in hits)


def test_grounded_simulator_never_fabricates_b2b_target_urls():
    pages = _sample_d2c_pages()
    kg = WebsiteKnowledgeGraph(brand="BrightSmile", domain="brightsmile.shop")
    kg.build_from_pages(pages)
    sim = GroundedAnswerSimulator(graph=kg, pages=pages)

    res = sim.simulate("Q-001", "Is BrightSmile compliant with safety and privacy standards?")
    # Must target an actual crawled URL, never fabricated /security or /documentation
    assert res.target_update_page != "/security"
    assert res.target_update_page != "/documentation"
    assert res.target_update_page.startswith("https://brightsmile.shop")


@pytest.mark.asyncio
async def test_dynamic_sandbox_uses_frontier_ai_for_questions_and_batched_rag():
    assert settings.USE_LLM_SANDBOX_SYNTHESIS is True
    pages = _sample_d2c_pages()
    profile = BusinessProfile(
        business_name="BrightSmile",
        business_model="D2C Ecommerce",
        industry="Oral Care",
        products=["Nano-Hydroxyapatite Toothpaste", "Sonic Toothbrush"],
        target_audience="Health-conscious consumers",
    )
    entity = ResolvedEntity(
        name="BrightSmile",
        domain="brightsmile.shop",
        niche="Oral Care",
        value_proposition="Enamel-safe daily oral care",
    )

    synth_calls = []
    rag_calls = []

    async def _fake_router(**kwargs):
        cap = kwargs.get("capability")
        if cap == "aeo_question_synthesis":
            synth_calls.append(kwargs)
            # Verify Evidence objects (not raw dicts!) are passed
            for ev in kwargs.get("evidence_list") or []:
                assert isinstance(ev, Evidence)
                assert len(ev.content_sha256 or "") == 64
            batch_num = len(synth_calls)
            return {
                "questions": [
                    {
                        "category_id": "product_ingredients",
                        "facet": "Product Ingredients & Specifications",
                        "question": f"What active ingredients are in BrightSmile toothpaste variant {batch_num}-{i}?",
                        "intent": "Verify ingredient disclosure",
                    }
                    for i in range(6)
                ]
            }
        if cap == "aeo_analysis":
            rag_calls.append(kwargs)
            import re as _re
            qids = _re.findall(r'"question_id":\s*"(Q-\d+)"', kwargs["task_contract"])
            return {
                "answers": [
                    {
                        "question_id": qid,
                        "rag_answer": "BrightSmile toothpaste uses nano-hydroxyapatite and is fluoride-free.",
                        "gap_analysis": "Ingredient percentages are not published.",
                        "missing_aspects": ["ingredient percentage"],
                        "target_update_url": "https://brightsmile.shop/products/toothpaste",
                        "section_update_recommendation": "Add full INCI percentages on the product page.",
                    }
                    for qid in qids
                ]
            }
        return {"status": "unavailable"}

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(side_effect=_fake_router)

    engine = DynamicQuestionSandboxEngine(model_router=mock_router)
    evals = await engine.generate_and_evaluate_100_questions(
        pages=pages,
        website_url="https://brightsmile.shop/",
        resolved_entity=entity,
        profile=profile,
        budget=QuestionBudgetTier.STARTER,  # 50 questions
    )

    assert len(evals) == 50
    assert len(synth_calls) >= 1
    assert len(rag_calls) == 5  # 50 questions / batch_size 10
    assert all(e.evaluation_trace.get("ai_rag_verified") is True for e in evals)
    assert all(e.target_update_page == "https://brightsmile.shop/products/toothpaste" for e in evals)


@pytest.mark.asyncio
async def test_cro_four_agents_use_frontier_ai_and_preserve_ga4_boundaries():
    bb = CognitiveBlackboard(run_id="cro_phase4", website_url="https://brightsmile.shop/")
    bb.pages = _sample_d2c_pages()
    bb.business_profile = BusinessProfile(business_name="BrightSmile", industry="Oral Care", business_model="D2C")
    bb.evidence_store.add(
        Evidence(
            id="ev_cro_sec_1",
            source_type="page_section",
            analyzer="crawler",
            url="https://brightsmile.shop/",
            selector="section#sec_hero",
            text="Enamel-Safe Daily Oral Care",
            content_sha256="b" * 64,
            hash="b" * 64,
        )
    )

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(
        return_value={
            "summary": "Hero CTA lacks price anchor near button.",
            "claims": [
                {
                    "statement": "Primary hero section lacks visible starting price next to Shop Starter Kit CTA.",
                    "severity": "MEDIUM",
                    "confidence": 0.85,
                    "evidence_refs": ["ev_cro_sec_1"],
                    "recommendation": "Show Rs 349 starting price beside CTA.",
                }
            ],
        }
    )

    for cls in (CroConversionAgent, VisualUxFrictionAgent, FormAbandonmentAgent, PricingTrustAgent):
        agent = cls(model_router=mock_router)
        res = await agent.run(bb)
        assert res["observations"]["ai_status"] == "completed"
        assert res["observations"]["requires_analytics"]["actual_conversion_rate"] == "UNKNOWN (Requires GA4 connector)"
        assert len(res["claims"]) == 1

    assert mock_router.generate_structured.await_count == 4
    assert len(bb.claim_registry.get_all()) == 4


@pytest.mark.asyncio
async def test_geo_enrichment_keeps_readiness_separate_from_live_visibility():
    pages = _sample_d2c_pages()
    profile = BusinessProfile(business_name="BrightSmile", industry="Oral Care")
    report = evaluate_geo_readiness(
        website_url="https://brightsmile.shop/",
        pages=pages,
        manifest=None,
        profile=profile,
        visibility_measured=False,
        visibility_score=None,
    )
    orig_extractability = report.extractability_score

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(
        return_value={
            "citation_readiness_summary": "Product specs are concise but lack clinical citation links.",
            "top_citation_gaps": ["Missing clinical study citations for enamel safety."],
            "quotable_block_recommendations": [
                {
                    "target_url": "https://brightsmile.shop/products/toothpaste",
                    "why": "AI engines quote concise Q&A definition blocks.",
                    "suggested_structure": "Add a 50-word formulation summary block.",
                }
            ],
        }
    )

    enriched = await enrich_geo_readiness_citations(
        report,
        model_router=mock_router,
        brand_name="BrightSmile",
        domain="brightsmile.shop",
        profile=profile,
    )
    assert enriched.extractability_score == orig_extractability
    assert enriched.visibility_status == "NOT_CONFIGURED"
    assert "ai_citation_readiness_synthesis" in (enriched.citation_passages or {})


def test_seo_enterprise_model_router_runner_adapter():
    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(
        return_value={"agent_id": "seo.ai.test", "version": "1.0", "status": "completed", "findings": []}
    )
    runner = build_model_router_runner(mock_router)
    out = runner("system prompt", "user payload", 30)
    assert out["status"] == "completed"

    # Unavailable response must fail closed with ModelNotRun
    mock_router_unavail = MagicMock()
    mock_router_unavail.generate_structured = AsyncMock(
        return_value={"status": "unavailable", "unavailable_reason": "no_llm_key"}
    )
    runner_unavail = build_model_router_runner(mock_router_unavail)
    with pytest.raises(ModelNotRun):
        runner_unavail("system prompt", "user payload", 30)
