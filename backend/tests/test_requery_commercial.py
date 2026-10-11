"""
Tests for 6 Commercial Inquiries Baseline & Re-Query After Patch
Verifies Identity, ICP, Pricing, Alternatives, Trust, and ROI evaluation and citation score gains.
"""
import pytest
from app.domain.models import BusinessProfile, CommercialQueryEvaluation
from app.workers.simulator_worker import CognitiveSimulatorWorker, CANONICAL_COMMERCIAL_QUESTIONS

def test_same_answer_does_not_raise_the_patch_score():
    from app.intelligence.citations.answer_change import answers_unchanged, settle_patch_scores

    before = "Cannot determine from crawled site evidence."
    after = "Cannot determine from crawled site evidence, as pricing information is not available."
    assert answers_unchanged(before, after) is True
    after_score, delta, gain = settle_patch_scores(1, 5, before, after, 0.40)
    assert after_score == 1
    assert delta == 0
    assert gain is None

    same_offer = "AlienHouse Networks is a professionally managed technology solutions company delivering secure, scalable, and high-performance digital systems for enterprises."
    cited_offer = same_offer + ", as stated in their meta description [EV_004]."
    assert answers_unchanged(same_offer, cited_offer) is True

    inferred = "AlienHouse Networks' product is built for enterprises, as stated in their meta description [EV_004]."
    assert answers_unchanged("Cannot determine from crawled site evidence.", inferred) is True

    new_fact_score, new_delta, new_gain = settle_patch_scores(
        3,
        8,
        "Pricing is not mentioned on the site.",
        "Pricing starts at $49/mo for standard teams.",
        0.50,
    )
    assert new_fact_score == 8
    assert new_delta == 5
    assert new_gain == 0.50


def test_canonical_commercial_questions_defined():
    assert len(CANONICAL_COMMERCIAL_QUESTIONS) == 6
    keys = [q["key"] for q in CANONICAL_COMMERCIAL_QUESTIONS]
    assert keys == ["identity", "icp", "pricing", "alternatives", "trust", "roi"]

@pytest.mark.asyncio
async def test_simulator_worker_fails_closed_when_model_offline():
    from unittest.mock import AsyncMock, MagicMock
    from app.cognition.blackboard import CognitiveBlackboard

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={})

    worker = CognitiveSimulatorWorker(worker_id="sim_test", model_router=mock_router)
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://acme.com")

    res = await worker.execute_task("ai_search_simulation", blackboard)
    assert res["status"] == "UNAVAILABLE"
    assert len(blackboard.commercial_evaluations) == 0

@pytest.mark.asyncio
async def test_simulator_worker_calculates_gain_from_structured_model_output():
    from unittest.mock import AsyncMock, MagicMock
    from app.cognition.blackboard import CognitiveBlackboard

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={
        "commercial_evaluations": [
            {
                "question_key": "pricing",
                "question_title": "Pricing & Commercial Model",
                "buyer_query": "How much does Acme cost?",
                "before_score": 3,
                "before_answer": "Pricing is not mentioned on the site.",
                "before_evidence_status": "MISSING",
                "after_score": 8,
                "after_answer": "Pricing starts at $49/mo for standard teams.",
                "delta": 5,
                "patch_citation_gain": 0.50,
                "evidence_snippet": "",
                "gap_analysis": "Pricing hidden behind sales contact."
            }
        ],
        "scenarios": []
    })

    worker = CognitiveSimulatorWorker(worker_id="sim_test", model_router=mock_router)
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://acme.com")
    blackboard.business_profile = BusinessProfile(
        business_name="Acme Metrics",
        niche="Enterprise Observability",
        value_proposition="Real-time latency analytics for microservices"
    )

    res = await worker.execute_task("ai_search_simulation", blackboard)
    assert len(blackboard.commercial_evaluations) == 1
    ev = blackboard.commercial_evaluations[0]
    assert ev.before_score == 3
    assert ev.after_score == 8
    assert ev.delta == 5
    assert ev.patch_citation_gain == 0.50
    assert ev.gap_analysis == "Pricing hidden behind sales contact."


@pytest.mark.asyncio
async def test_simulator_does_not_raise_a_score_when_the_after_answer_is_the_same():
    from unittest.mock import AsyncMock, MagicMock
    from app.cognition.blackboard import CognitiveBlackboard

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={
        "commercial_evaluations": [
            {
                "question_key": "pricing",
                "question_title": "Pricing & Commercial Model",
                "buyer_query": "How much does Acme cost?",
                "before_score": 1,
                "before_answer": "Cannot determine from crawled site evidence.",
                "before_evidence_status": "MISSING",
                "after_score": 5,
                "after_answer": "Cannot determine from crawled site evidence, as pricing information is not available.",
                "delta": 4,
                "patch_citation_gain": 0.40,
                "evidence_snippet": "",
                "gap_analysis": "Pricing information is not available on the website."
            }
        ],
        "scenarios": []
    })

    worker = CognitiveSimulatorWorker(worker_id="sim_test", model_router=mock_router)
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://acme.com")
    blackboard.business_profile = BusinessProfile(
        business_name="Acme Metrics",
        niche="Enterprise Observability",
        value_proposition="Real-time latency analytics for microservices"
    )

    await worker.execute_task("ai_search_simulation", blackboard)
    ev = blackboard.commercial_evaluations[0]
    assert ev.before_score == 1
    assert ev.after_score == 1
    assert ev.delta == 0
    assert ev.patch_citation_gain is None

@pytest.mark.asyncio
async def test_simulator_worker_evaluates_all_6_canonical_questions():
    from unittest.mock import AsyncMock, MagicMock
    from app.cognition.blackboard import CognitiveBlackboard

    mock_router = MagicMock()
    mock_router.generate_structured = AsyncMock(return_value={
        "commercial_evaluations": [
            {
                "question_key": "identity",
                "question_title": "1. Identity & Category",
                "buyer_query": "What does Acme do?",
                "before_score": 7,
                "before_answer": "Acme is a cloud observability platform.",
                "before_evidence_status": "VERIFIED",
                "after_score": 9,
                "after_answer": "Acme is an enterprise Kubernetes observability platform.",
                "delta": 2,
                "patch_citation_gain": 0.20,
                "evidence_snippet": "Cloud observability platform",
                "gap_analysis": "Needs deeper Schema.org Organization markup."
            },
            {
                "question_key": "pricing",
                "question_title": "3. Pricing & Commercial Model",
                "buyer_query": "How much does Acme cost?",
                "before_score": 3,
                "before_answer": "Pricing not listed on site.",
                "before_evidence_status": "MISSING",
                "after_score": 8,
                "after_answer": "Pricing starts at $49/mo.",
                "delta": 5,
                "patch_citation_gain": 0.50,
                "evidence_snippet": "",
                "gap_analysis": "Pricing hidden behind sales demo."
            }
        ],
        "scenarios": []
    })

    worker = CognitiveSimulatorWorker(worker_id="sim_test", model_router=mock_router)
    blackboard = CognitiveBlackboard(run_id="test_run", website_url="https://acme.com")
    blackboard.business_profile = BusinessProfile(
        business_name="Acme Metrics",
        niche="Enterprise Observability",
        value_proposition="Real-time latency analytics for microservices"
    )

    res = await worker.execute_task("ai_search_simulation", blackboard)
    assert res["status"] == "AVAILABLE"
    # All 6 canonical questions must be populated
    assert len(blackboard.commercial_evaluations) == 6
    assert len(blackboard.ai_search_evaluations) == 6

    # Verify each has the expected canonical keys and numbered titles
    keys = [e.question_key for e in blackboard.commercial_evaluations]
    assert keys == ["identity", "icp", "pricing", "alternatives", "trust", "roi"]

    # Verify AiSearchQueryEvaluation items carry citation probability and post-patch projections
    for item in blackboard.ai_search_evaluations:
        assert item.score is not None
        assert item.citation_probability is not None
        assert item.detected_answer
        assert item.after_score is not None

