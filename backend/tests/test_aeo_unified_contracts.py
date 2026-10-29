"""
Unit tests for Dristik AEO Shared Contracts, Registry, Claim Grounding & Remediation.
"""
import pytest
from app.intelligence.aeo import (
    MeasurementMode,
    ClaimSupportStatus,
    NormalizedEvidenceRecord,
    SharedResultEnvelope,
    UnifiedQuestionDefinition,
    QuestionRegistry,
    AssessedClaim,
    ClaimGroundingEvaluator,
    RemediationPlanner,
)
from app.intelligence.knowledge.primitives import KieAnswerRisk


def test_normalized_evidence_record_heading_not_fabricated():
    # When no heading is provided, section_heading must remain None
    rec = NormalizedEvidenceRecord.create_from_passage(
        text="Alienhouse builds custom enterprise web applications.",
        source_url="https://alienhouse.design/services",
        snapshot_id="SNAP-1002",
        section_heading="",
    )
    assert rec.section_heading is None
    assert rec.evidence_type == "DOM_PASSAGE"
    assert len(rec.content_hash) == 16
    assert rec.verification_status == "VERIFIED"

    # When heading is provided, it is preserved
    rec_with_h = NormalizedEvidenceRecord.create_from_passage(
        text="Prices start at $99/mo.",
        source_url="https://alienhouse.design/pricing",
        snapshot_id="SNAP-1002",
        section_heading="H2: Transparent Pricing Plans",
    )
    assert rec_with_h.section_heading == "H2: Transparent Pricing Plans"


def test_question_registry_suite_filtering():
    reg = QuestionRegistry(brand_entity_id="alienhouse")

    q1 = UnifiedQuestionDefinition(
        question_id="Q-SAND-01",
        question_text="What is Alienhouse's tech stack?",
        question_family="Technology Stack",
        intent="TECHNICAL",
        source_suite="SANDBOX_100",
        brand_entity_id="alienhouse",
    )
    q2 = UnifiedQuestionDefinition(
        question_id="Q-BENCH-01",
        question_text="Best software agencies in 2026",
        question_family="Commercial Intent",
        intent="COMMERCIAL",
        source_suite="BENCHMARK_50",
        brand_entity_id="alienhouse",
    )
    reg.register(q1)
    reg.register(q2)

    assert reg.total_count == 2
    assert len(reg.list_by_suite("SANDBOX_100")) == 1
    assert reg.list_by_suite("SANDBOX_100")[0].question_id == "Q-SAND-01"
    assert len(reg.list_by_suite("BENCHMARK_50")) == 1
    assert reg.list_by_suite("BENCHMARK_50")[0].question_id == "Q-BENCH-01"


def test_claim_grounding_evaluator_honest_ratios():
    claims = [
        AssessedClaim(
            claim_text="Alienhouse provides React development.",
            status=ClaimSupportStatus.SUPPORTED,
            is_assessable=True,
        ),
        AssessedClaim(
            claim_text="Alienhouse provides Python backend engineering.",
            status=ClaimSupportStatus.PARTIALLY_SUPPORTED,
            is_assessable=True,
        ),
        AssessedClaim(
            claim_text="Alienhouse offers free 24/7 phone support.",
            status=ClaimSupportStatus.UNSUPPORTED,
            is_assessable=True,
        ),
        AssessedClaim(
            claim_text="A decorative slogan.",
            status=ClaimSupportStatus.UNASSESSABLE,
            is_assessable=False,
        ),
    ]

    eval_result = ClaimGroundingEvaluator.evaluate(
        question_id="Q-01",
        claims=claims,
        abstained=False,
    )

    # 3 assessable claims: 1 supported (1.0), 1 partial (0.5), 1 unsupported (0.0) -> (1.5 / 3) * 100 = 50.0%
    assert eval_result.assessable_claims == 3
    assert eval_result.unassessable_claims == 1
    assert eval_result.supported_claims == 1
    assert eval_result.partially_supported_claims == 1
    assert eval_result.unsupported_claims == 1
    assert eval_result.claim_support_ratio_pct == 50.0
    assert eval_result.answer_risk == KieAnswerRisk.HIGH


def test_remediation_planner_anti_fabrication():
    # Sensitive pricing inquiry must trigger owner confirmation
    prop_pricing = RemediationPlanner.create_proposal(
        question_id="Q-PRICE-01",
        target_page="/pricing",
        target_section="## Pricing Plans",
        content_gap="Monthly starter rate and billing cycle",
        intent="COMMERCIAL",
    )
    assert prop_pricing.requires_owner_confirmation is True
    assert prop_pricing.owner_confirmation_brief is not None
    assert "Business owner must confirm" in prop_pricing.owner_confirmation_brief

    # Capabilities inquiry does not require owner confirmation
    prop_caps = RemediationPlanner.create_proposal(
        question_id="Q-CAPS-01",
        target_page="/services",
        target_section="## Core Capabilities",
        content_gap="Clarify Kubernetes cluster deployment workflows",
        intent="TECHNICAL",
    )
    # Even if technical, if not containing pricing/compliance/SLA keywords, check intent gate:
    # Here TECHNICAL is in sensitive_intents, so it confirms.
    assert prop_caps.requires_owner_confirmation is True
