"""Tests for Phase 2: Rigorous AI Visibility Engine & Platform-Specific AI Crawler Matrix."""
from app.aeo.intelligence.visibility_engine import (
    INTENT_CLASSES,
    RigorousAiVisibilityEngine,
    build_ai_crawler_matrix,
    generate_classified_question_set,
)


def test_question_universe_generation_and_classification():
    qs = generate_classified_question_set(
        brand_name="Perfora",
        category="electric toothbrush",
        products=["Truthbrush", "Smart Water Flosser"],
        competitors=["Oral-B", "Colgate"],
        target_count=120,
    )
    assert len(qs) == 120
    intents_seen = {q.intent_class for q in qs}
    assert intents_seen == set(INTENT_CLASSES)


def test_rigorous_execution_methods_volatility_and_unmeasured_surfaces():
    qs = generate_classified_question_set(brand_name="Perfora", category="oral care", target_count=10)
    executions = [
        # Perplexity live search trial 1 (cited + mentions brand & Oral-B)
        {
            "query_id": "Q-001", "query_text": "Perfora Truthbrush price in India", "intent_class": "transactional",
            "engine_id": "perplexity_sonar", "model_version": "sonar-pro", "trial_number": 1,
            "raw_response": "Perfora Truthbrush costs ₹1499 and competes with Oral-B.",
            "citations": ["https://perforacare.com/products/truthbrush", "https://oralb.in/brush"],
        },
        # Perplexity live search trial 2 (volatile: not cited on repeat run)
        {
            "query_id": "Q-001", "query_text": "Perfora Truthbrush price in India", "intent_class": "transactional",
            "engine_id": "perplexity_sonar", "model_version": "sonar-pro", "trial_number": 2,
            "raw_response": "Perfora Truthbrush costs ₹1499.",
            "citations": ["https://amazon.in/truthbrush"],
        },
        # Consumer UI surface MUST remain UNMEASURED
        {
            "query_id": "Q-001", "query_text": "Perfora Truthbrush price in India",
            "engine_id": "chatgpt_search_consumer_ui",
        },
    ]
    summary = RigorousAiVisibilityEngine.evaluate_observations(
        domain="perforacare.com",
        brand_name="Perfora",
        queries=qs,
        raw_executions=executions,
        competitors=["Oral-B", "Colgate"],
        verified_facts={"price": "₹1499"},
    )
    assert summary.valid_executions == 2
    assert "chatgpt_search_consumer_ui" in summary.unmeasured_engines
    assert summary.execution_methods_used["perplexity_sonar"] == "LIVE_WEB_SEARCH"
    assert summary.execution_methods_used["chatgpt_search_consumer_ui"] == "UNOBSERVABLE"
    # 1 of 2 cited, 2 of 2 mentioned -> strictly separate
    assert summary.citation_rate_pct == 50.0
    assert summary.brand_mention_rate_pct == 100.0
    assert summary.volatility_score_pct == 100.0
    assert summary.citation_persistence_pct == 0.0
    assert summary.answer_accuracy_pct == 100.0


def test_ai_crawler_matrix_separates_training_search_and_retrieval():
    robots = """
    User-agent: GPTBot
    Disallow: /

    User-agent: OAI-SearchBot
    Allow: /

    User-agent: ChatGPT-User
    Allow: /
    """
    res = build_ai_crawler_matrix(robots)
    assert res["robots_measured"] is True
    by_bot = {row["bot"]: row for row in res["matrix"]}
    assert by_bot["GPTBot"]["category"] == "training_crawlers"
    assert by_bot["GPTBot"]["access_status"] == "BLOCKED"
    assert by_bot["OAI-SearchBot"]["category"] == "search_crawlers"
    assert by_bot["OAI-SearchBot"]["access_status"] == "ALLOWED"
    assert by_bot["ChatGPT-User"]["category"] == "retrieval_fetchers"
    assert by_bot["ChatGPT-User"]["access_status"] == "ALLOWED"
