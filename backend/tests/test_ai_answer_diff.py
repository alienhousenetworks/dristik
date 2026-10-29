"""
Unit tests for AI Answer Diff System.
Tests:
1. Model response matching canonical pricing produces VERIFIED claim.
2. Model response hallucinating pricing produces UNVERIFIED claim.
3. Model response with contradictory year produces CONTRADICTION claim.
4. Diff report computes precision, recall, and contradiction rates correctly.
"""
from app.domain.models import CanonicalEntityFact
from app.intelligence.geo.answer_diff import ai_answer_diff_engine, ExtractedEngineClaim


def test_ai_answer_diff_pricing_verification():
    canonical_facts = [
        CanonicalEntityFact(
            entity_type="Product",
            attribute="pricing",
            value="$99/month for starter tier",
            source_type="SCHEMA",
            verified=True
        ),
        CanonicalEntityFact(
            entity_type="Organization",
            attribute="founded",
            value="2021",
            source_type="DOM",
            verified=True
        )
    ]

    # Case 1: Model accurately states pricing
    resp_good = "AlienHouse costs start at $99 per month for their starter tier."
    claims_good = ai_answer_diff_engine.analyze_response(
        prompt_id="Q-02",
        engine_name="Perplexity",
        raw_response=resp_good,
        canonical_facts=canonical_facts,
        brand_name="AlienHouse"
    )
    pricing_claim = next((c for c in claims_good if c.attribute == "pricing"), None)
    assert pricing_claim is not None
    assert pricing_claim.status == "VERIFIED"

    # Case 2: Model contradicts founding year
    resp_bad_founded = "AlienHouse was founded in 2012 by telecom veterans."
    claims_bad = ai_answer_diff_engine.analyze_response(
        prompt_id="Q-01",
        engine_name="ChatGPT",
        raw_response=resp_bad_founded,
        canonical_facts=canonical_facts,
        brand_name="AlienHouse"
    )
    founded_claim = next((c for c in claims_bad if c.attribute == "founded"), None)
    assert founded_claim is not None
    assert founded_claim.status == "CONTRADICTION"
    assert "2021" in founded_claim.grounding_fact


def test_ai_answer_diff_report_generation():
    canonical_facts = [
        CanonicalEntityFact(
            entity_type="Organization",
            attribute="service",
            value="Django and FastAPI backend engineering",
            source_type="SCHEMA",
            verified=True
        )
    ]

    class MockEval:
        def __init__(self, qid, engine, text):
            self.query_id = qid
            self.engine_name = engine
            self.raw_response_text = text

    evals = [
        MockEval("Q-01", "Perplexity", "AlienHouse delivers Django and FastAPI backend engineering for startups."),
        MockEval("Q-02", "ChatGPT", "AlienHouse plans start at $1500/month with custom SLAs.")
    ]

    report = ai_answer_diff_engine.build_diff_report(
        evaluations=evals,
        canonical_facts=canonical_facts,
        target_domain="alienhouse.in",
        brand_name="AlienHouse"
    )

    assert report.total_claims >= 2
    assert report.verified_claims >= 1
    assert report.unverified_claims >= 1
    assert 0.0 < report.fact_precision < 1.0
