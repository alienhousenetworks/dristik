"""
Unit tests for the AEO Complete Blueprint Enhancements.
Tests:
1. Stage A Relevance Gating: Irrelevant passages fail Stage A and receive 0% grounding.
2. Question Universe: Priority formula and discovery agent blackboard integration.
3. Live AI Visibility: Truthful reporting when credentials are unconfigured.
4. UrlFrontier: Lifecycle state machine and representative sampling disclosure.
5. GA4: AI referral domain classifier.
"""
import pytest
from app.aeo.intelligence.factual_grounding_pipeline import (
    FactualGroundingPipeline,
    AnswerabilityState,
)
from app.aeo.intelligence.question_universe import (
    QuestionUniverseGenerator,
    QuestionIntent,
    BusinessImportance,
    compute_question_priority,
)
from app.aeo.intelligence.live_answer_evaluation import (
    LiveAnswerEvaluationEngine,
)
from app.crawl.url_frontier import UrlFrontier, UrlCrawlState
from app.connectors.google.ga4_connector import classify_ai_referral


def test_stage_a_relevance_gate_rejects_irrelevant_passage():
    # Irrelevant passage (about agency services) tested against an oral-care question
    question = "What makes Perfora electric toothbrush different from conventional brushes?"
    irrelevant_passage = "We are a full-service B2B digital marketing agency delivering Next.js applications and cloud architecture."

    passed, reason = FactualGroundingPipeline.validate_stage_a_relevance(
        question=question,
        passage_text=irrelevant_passage,
        target_entities=["Perfora", "electric toothbrush"],
    )
    assert passed is False
    assert "Stage A Relevance Failed" in reason

    # Evaluation returns UNANSWERABLE with 0% grounding
    result = FactualGroundingPipeline.evaluate_grounded_answerability(
        question=question,
        candidate_passages=[{"url": "https://example.com/about", "text": irrelevant_passage, "entities": ["agency"]}],
        claims=["Perfora uses sonic vibrations."],
        empirical_catalog={"products": ["electric toothbrush"]},
    )
    assert result.relevance_passed is False
    assert result.answerability_state == AnswerabilityState.UNANSWERABLE
    assert result.grounding_score_pct == 0.0


def test_stage_a_relevance_gate_accepts_relevant_passage():
    question = "What is the battery life of Perfora electric toothbrush?"
    relevant_passage = "The Perfora electric toothbrush features a 90-day rechargeable lithium battery with sonic vibrations."

    passed, reason = FactualGroundingPipeline.validate_stage_a_relevance(
        question=question,
        passage_text=relevant_passage,
        target_entities=["Perfora", "electric toothbrush"],
    )
    assert passed is True
    assert reason is None

    result = FactualGroundingPipeline.evaluate_grounded_answerability(
        question=question,
        candidate_passages=[{"url": "https://perfora.co/toothbrush", "text": relevant_passage, "entities": ["Perfora"]}],
        claims=["The electric toothbrush has clinical battery life."],
        empirical_catalog={"products": ["electric toothbrush"]},
    )
    assert result.relevance_passed is True
    assert result.grounding_score_pct >= 90.0
    assert result.answerability_state == AnswerabilityState.ANSWERABLE


def test_question_priority_formula():
    # P = 0.30I + 0.25B + 0.20G + 0.15C + 0.10E
    # Transactional (100) + Critical (100) + Commercial (90)
    priority = compute_question_priority(
        intent=QuestionIntent.TRANSACTIONAL,
        importance=BusinessImportance.CRITICAL,
        has_evidence=True,
        is_commercial=True,
    )
    assert priority >= 80.0


def test_question_universe_from_discovery_agents():
    class DummyPage:
        title = "Perfora | Modern Oral Care"
        h1 = ["Electric Toothbrush", "Smart Water Flosser"]

    class DummyBlackboard:
        site_facts = {"site_name": "Perfora"}
        business_profile = None
        pages = [DummyPage()]

    report = QuestionUniverseGenerator.from_blackboard_discovery(
        domain="perfora.co",
        blackboard=DummyBlackboard(),
    )
    assert report.brand_name == "Perfora"
    assert len(report.questions) > 0
    # Questions must reference oral care or products from ProductPerspectiveAgent, not sensitive gums if not declared
    first_q = report.questions[0]
    assert "Electric Toothbrush" in first_q.question_text


def test_url_frontier_lifecycle_and_sampling_disclosure():
    frontier = UrlFrontier("example.com", "https://example.com")
    
    # 5 discovered URLs
    for path in ["/", "/products", "/pricing", "/about", "/blog"]:
        frontier.admit(f"https://example.com{path}")

    # Inspect only 2 URLs (simulating shallow sampling)
    frontier.mark_state("https://example.com/", UrlCrawlState.FETCHED)
    frontier.mark_state("https://example.com/products", UrlCrawlState.ANALYZED)

    summary = frontier.get_coverage_summary()
    assert summary["discovered_count"] == 5
    assert summary["inspected_count"] == 2
    assert summary["is_representative_sample"] is True
    assert summary["sampling_scope"] == "REPRESENTATIVE"
    assert "Sampled 2 of 5 discovered URLs" in summary["sampling_note"]


def test_live_ai_unconfigured_status_handling():
    report = LiveAnswerEvaluationEngine.evaluate_live_answers(
        domain="example.com",
        brand_name="ExampleBrand",
        tested_queries=[],
    )
    assert report.total_questions_tested == 0
    assert report.direct_answer_rate_pct == 0.0
    assert report.citation_correctness_rate_pct == 0.0
    assert report.connection_status == "CREDENTIALS_NOT_CONFIGURED"
    assert "citation metrics remain unmeasured rather than simulated" in report.status_note


def test_ga4_ai_referral_classification():
    assert classify_ai_referral("chatgpt.com") == "ChatGPT"
    assert classify_ai_referral("chat.openai.com") == "ChatGPT"
    assert classify_ai_referral("www.perplexity.ai") == "Perplexity"
    assert classify_ai_referral("claude.ai") == "Claude"
    assert classify_ai_referral("gemini.google.com") == "Gemini"
    assert classify_ai_referral("google.com") is None
    assert classify_ai_referral("facebook.com") is None


def test_contradiction_detector_finds_discrepancies():
    from app.aeo.intelligence.contradiction_detector import ContradictionDetector, ConflictSeverity

    pages = {
        "https://example.com/pricing": "Enjoy our 30-day money-back guarantee with free shipping on orders over $50.",
        "https://example.com/faq": "We provide a 14-day return window and free shipping on orders over $75. Call our helpline at (800) 555-0199.",
        "https://example.com/contact": "Need help? Call our official support at (800) 555-9999.",
    }

    report = ContradictionDetector.audit_pages(pages, domain="example.com")
    assert report.total_conflicts >= 3
    # Check fields detected
    fields = [c.field for c in report.conflicts]
    assert "Return Policy Window" in fields
    assert "Free Shipping Threshold" in fields
    assert "Customer Support Phone Number" in fields
    assert report.consistency_score < 100.0

