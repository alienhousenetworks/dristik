"""
Tests for 1-Competitor Bake-Off Engine
Verifies comparative evaluations across target vs competitor on the 6 commercial inquiries.
"""
import pytest
from app.domain.models import BusinessProfile, CommercialQueryEvaluation
from app.intelligence.competitive.bakeoff import CommercialBakeoffEngine

@pytest.mark.asyncio
async def test_commercial_bakeoff_execution():
    engine = CommercialBakeoffEngine()
    target_bp = BusinessProfile(
        business_name="Dristik AI",
        niche="Website Intelligence",
        value_proposition="Autonomous website intelligence with verified DOM evidence."
    )
    target_evals = [
        CommercialQueryEvaluation(
            question_key="identity",
            question_title="Identity & Category",
            buyer_query="What is Dristik AI?",
            before_score=8,
            before_answer="Dristik AI is an autonomous website intelligence platform.",
            before_evidence_status="VERIFIED"
        ),
        CommercialQueryEvaluation(
            question_key="pricing",
            question_title="Pricing & Commercial Model",
            buyer_query="How much does Dristik cost?",
            before_score=7,
            before_answer="Pricing starts at ₹49,000 for diagnostic audits.",
            before_evidence_status="VERIFIED"
        ),
        CommercialQueryEvaluation(
            question_key="icp",
            question_title="Target Audience & ICP",
            buyer_query="Who is Dristik built for?",
            before_score=8,
            before_answer="Built for SaaS founders, engineering leaders, and growth marketers.",
            before_evidence_status="VERIFIED"
        )
    ]

    # 1. Uncrawled competitor fails closed with INSUFFICIENT_EVIDENCE
    uncrawled_res = await engine.execute_bakeoff(
        target_profile=target_bp,
        target_evals=target_evals,
        competitor_url="https://profound.com"
    )
    assert uncrawled_res.competitor_domain == "profound.com"
    assert uncrawled_res.status == "INSUFFICIENT_EVIDENCE"
    assert len(uncrawled_res.evaluations) == 0
    assert "has not been crawled" in uncrawled_res.executive_takeaway

    # 2. Crawled competitor with profile executes evidence-grounded bake-off
    comp_bp = BusinessProfile(
        business_name="Profound",
        niche="Website Intelligence",
        value_proposition="Enterprise website search analytics"
    )
    res = await engine.execute_bakeoff(
        target_profile=target_bp,
        target_evals=target_evals,
        competitor_url="https://profound.com",
        competitor_profile=comp_bp
    )

    assert res.competitor_domain == "profound.com"
    assert res.status == "AVAILABLE"
    assert len(res.evaluations) == 6
    assert all(item.winner == "unmeasured" for item in res.evaluations)
    assert len(res.executive_takeaway) > 20
