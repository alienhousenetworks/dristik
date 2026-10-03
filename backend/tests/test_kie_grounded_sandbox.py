"""
Unit and Integration Test Suite for Hardened KIE Grounded Sandbox Engine.
Verifies DOM noise sanitization, topic relevance gating, evidence sufficiency,
non-circular claim verification, and zero false-answerability against ground truth.
"""
import json
import os
import pytest
from app.domain.models import PageEvidence, ResolvedEntity
from app.intelligence.knowledge.claim_extractor import AtomicClaimExtractor, _sanitize_sentence, _split_sentences
from app.intelligence.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph
from app.intelligence.knowledge.evidence_sufficiency import EvidenceSufficiencyEvaluator
from app.intelligence.knowledge.grounded_simulator import GroundedAnswerSimulator
from app.intelligence.retrieval.hybrid_retriever import HybridRetriever, QueryPlanner
from app.intelligence.geo.dynamic_sandbox import DynamicQuestionSandboxEngine


def test_sanitizer_cleans_dom_noise():
    raw_text = (
        "System Module // megaphone Marketing Boost your online presence and grow your business "
        "with strategic digital marketing solutions. >> System_Overview We provide comprehensive "
        "digital marketing services including SEO, social media management, PPC campaigns, "
        "email marketing, and content strategy to help your brand reach the right audience "
        "and achieve measurable results. Explore With The Game //"
    )
    cleaned_sentences = _split_sentences(raw_text)
    assert len(cleaned_sentences) >= 1
    for s in cleaned_sentences:
        assert "//" not in s
        assert ">>" not in s
        assert "megaphone" not in s.lower()
        assert "explore with the game" not in s.lower()
        assert "system_overview" not in s.lower()
        assert "system module" not in s.lower()


def test_hybrid_retriever_zero_evidence_on_unanswerable_pricing():
    # Setup AlienHouse pages without pricing or security claims
    pages = [
        PageEvidence(
            url="https://alienhousenetworks.com/services/marketing",
            title="Marketing Services | AlienHouse Networks",
            h1=["Digital Marketing Solutions"],
            body_text=(
                "AlienHouse Networks delivers secure, scalable, and high-performance digital systems for enterprises. "
                "We provide comprehensive digital marketing services including SEO, social media management, "
                "PPC campaigns, email marketing, and content strategy."
            )
        )
    ]
    kg = WebsiteKnowledgeGraph("AlienHouse Networks", "alienhousenetworks.com")
    kg.build_from_pages(pages)

    retriever = HybridRetriever(kg)
    q = "What are AlienHouse Networks' exact pricing tiers and monthly subscription rates?"
    plan = QueryPlanner.plan(q)
    chunks = retriever.retrieve(q, plan)

    # Must return ZERO chunks because there is no pricing evidence
    assert len(chunks) == 0

    simulator = GroundedAnswerSimulator(kg)
    sim = simulator.simulate("Q-PRICING", q)
    assert sim.grounding_ratio == 0.0
    assert sim.answer_risk.value == "HIGH"
    assert sim.assessment_status == "INSUFFICIENT"
    assert "not published" in sim.candidate_answer.lower() or "not disclosed" in sim.candidate_answer.lower()


def test_hybrid_retriever_retrieves_clean_evidence_for_services():
    pages = [
        PageEvidence(
            url="https://alienhousenetworks.com/services/marketing",
            title="Marketing Services | AlienHouse Networks",
            h1=["Digital Marketing Solutions"],
            body_text=(
                "AlienHouse Networks delivers secure, scalable, and high-performance digital systems for enterprises. "
                "We provide comprehensive digital marketing services including SEO, social media management, "
                "PPC campaigns, email marketing, and content strategy."
            )
        )
    ]
    kg = WebsiteKnowledgeGraph("AlienHouse Networks", "alienhousenetworks.com")
    kg.build_from_pages(pages)

    retriever = HybridRetriever(kg)
    q = "What digital marketing services does AlienHouse Networks provide?"
    plan = QueryPlanner.plan(q)
    chunks = retriever.retrieve(q, plan)

    assert len(chunks) >= 1
    top_chunk = chunks[0]
    assert "marketing" in top_chunk.claim.object.lower() or "marketing" in top_chunk.claim.evidence.exact_sentence.lower()

    simulator = GroundedAnswerSimulator(kg)
    sim = simulator.simulate("Q-SERVICES", q)
    assert sim.grounding_ratio >= 0.50
    assert sim.assessment_status == "SUFFICIENT"
    assert sim.retrieval_evidence_count >= 1


def test_evidence_sufficiency_detects_partial_questions():
    pages = [
        PageEvidence(
            url="https://alienhousenetworks.com/services/marketing",
            title="Marketing Services | AlienHouse Networks",
            h1=["Digital Marketing Solutions"],
            body_text=(
                "AlienHouse Networks provides digital marketing services including SEO, PPC campaigns, and content strategy."
            )
        )
    ]
    kg = WebsiteKnowledgeGraph("AlienHouse Networks", "alienhousenetworks.com")
    kg.build_from_pages(pages)

    q = "What digital marketing services does AlienHouse Networks provide and what is their pricing?"
    simulator = GroundedAnswerSimulator(kg)
    sim = simulator.simulate("Q-PARTIAL", q)

    # Must be marked PARTIAL because services are covered but pricing is missing
    assert sim.assessment_status == "PARTIAL"
    assert len(sim.missing_aspects) >= 1
    assert any("price" in asp.lower() or "pricing" in asp.lower() for asp in sim.missing_aspects)
    # Grounding ratio should be scaled down to reflect partial coverage
    assert 0.0 < sim.grounding_ratio < 0.80


@pytest.mark.asyncio
async def test_alienhouse_ground_truth_fixture_evaluation():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "alienhouse_ground_truth.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture = json.load(f)

    brand = fixture["brand"]
    pages = [
        PageEvidence(
            url="https://alienhousenetworks.com/",
            title="AlienHouse Networks | Technology Solutions",
            h1=["Enterprise Digital Systems"],
            body_text=(
                "AlienHouse Networks is a professionally managed technology solutions company delivering secure, "
                "scalable, and high-performance digital systems for enterprises. We craft custom software, modern platforms, "
                "and digital experiences. Contact our team to request a custom build."
            )
        ),
        PageEvidence(
            url="https://alienhousenetworks.com/services/marketing",
            title="Digital Marketing | AlienHouse Networks",
            h1=["Strategic Marketing Services"],
            body_text=(
                "Boost your online presence and grow your business with strategic digital marketing solutions. "
                "AlienHouse Networks provides comprehensive digital marketing services including SEO, social media management, "
                "PPC campaigns, email marketing, and content strategy."
            )
        ),
        PageEvidence(
            url="https://alienhousenetworks.com/services/ai-engineering",
            title="AI Engineering | AlienHouse Networks",
            h1=["AI Solutions & Intelligent Workflows"],
            body_text=(
                "We engineer generative AI pipelines, intelligent agentic workflows, and automated reasoning systems. "
                "Our AI solutions integrate with enterprise infrastructure."
            )
        )
    ]

    kg = WebsiteKnowledgeGraph(brand, fixture["domain"])
    kg.build_from_pages(pages)
    simulator = GroundedAnswerSimulator(kg)

    for item in fixture["questions"]:
        q_id = item["id"]
        q_text = item["question"]
        expected_status = item["expected_status"]

        sim = simulator.simulate(q_id, q_text)

        # Check telemetry integrity
        assert sim.grounding_ratio is not None
        assert 0.0 <= sim.grounding_ratio <= 1.0
        assert sim.answer_risk in ["LOW", "MEDIUM", "HIGH"]

        status_map = {"SUFFICIENT": "ANSWERABLE", "INSUFFICIENT": "EVIDENCE_GAP", "PARTIAL": "PARTIAL"}
        mapped_status = status_map.get(sim.assessment_status, sim.assessment_status)
        assert mapped_status == expected_status, f"Question {q_id} expected {expected_status} but got {mapped_status} (raw={sim.assessment_status}). Answer: {sim.candidate_answer}"

        if expected_status == "EVIDENCE_GAP":
            # Must NEVER be falsely called answerable
            assert sim.grounding_ratio == 0.0 or sim.retrieval_evidence_count == 0
            assert sim.answer_risk == "HIGH"
            assert any(k in sim.candidate_answer.lower() for k in ["not published", "not disclosed", "not discovered", "not declared", "not found"])
        elif expected_status == "ANSWERABLE":
            assert sim.grounding_ratio >= 0.50
            assert sim.retrieval_evidence_count >= 1
        elif expected_status == "PARTIAL":
            assert len(sim.missing_aspects) >= 1
