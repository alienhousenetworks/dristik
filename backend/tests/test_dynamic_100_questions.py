"""
Unit and Integration Tests for Dynamic 100-Question AI Sandbox Engine
Verifies that 100 bespoke business questions are synthesized from scratch (zero hardcoded templates),
and every question evaluates whether an answer is possible, providing the concrete crawled answer,
evidence quotes, citability gap analysis, and recommended remediation answers.
"""
import pytest
from app.domain.models import PageEvidence, BusinessProfile, ResolvedEntity
from app.intelligence.geo.dynamic_sandbox import DynamicQuestionSandboxEngine, SANDBOX_FACETS
from app.intelligence.business.entity_resolver import UniversalEntityResolver


@pytest.mark.asyncio
async def test_dynamic_sandbox_generates_exact_100_questions_from_zero():
    # Setup mock business crawled pages
    pages = [
        PageEvidence(
            url="https://acme-observability.io/",
            title="Acme Observability | Real-time Microservice Latency Analytics",
            h1=["Autonomous Microservice Telemetry Platform"],
            h2=["Enterprise Real-Time APM", "Transparent Pricing & Open Architecture"],
            body_text=(
                "Acme Observability provides autonomous real-time latency monitoring for Kubernetes and microservices. "
                "Founded in 2022 by distributed systems engineers, Acme is headquartered in San Francisco, CA. "
                "Our platform is built for DevOps directors and SRE teams managing high-volume cloud infrastructure. "
                "Pricing starts at $99 per cluster per month for our Starter tier, with custom Enterprise plans. "
                "We provide full REST APIs, Prometheus webhooks, and native AWS CloudWatch integration. "
                "Acme is SOC 2 Type II certified and enforces AES-256 encryption at rest. "
                "Customer teams experience a 45% reduction in MTTR within the first 14 days of deployment. "
                "Contact sales or book a demo at https://acme-observability.io/demo."
            ),
            word_count=180
        ),
        PageEvidence(
            url="https://acme-observability.io/pricing",
            title="Pricing Plans | Acme Observability",
            h1=["Predictable Cluster Pricing"],
            body_text="Starter: $99/mo per cluster. Pro: $299/mo per cluster. Enterprise: Contact sales for multi-region SLAs.",
            word_count=60
        )
    ]

    resolved_entity = UniversalEntityResolver.resolve_from_evidence(
        website_url="https://acme-observability.io",
        pages=pages
    )

    # Assert brand is correctly identified and NOT "Unknown Business"
    assert resolved_entity.name in ["Acme Observability", "Acme", "Acme-observability"]
    assert "unknown" not in resolved_entity.name.lower()

    sandbox = DynamicQuestionSandboxEngine()
    evaluations = await sandbox.generate_and_evaluate_100_questions(
        pages=pages,
        website_url="https://acme-observability.io",
        resolved_entity=resolved_entity
    )

    # 1. Verify exactly 100 questions were generated
    assert len(evaluations) == 100
    assert len(SANDBOX_FACETS) == 10

    # 2. Verify all 10 facets are represented with 10 questions each
    facet_counts = {}
    for ev in evaluations:
        facet_counts[ev.facet] = facet_counts.get(ev.facet, 0) + 1
    assert len(facet_counts) == 10
    for f_title, count in facet_counts.items():
        assert count == 10, f"Facet '{f_title}' did not have 10 questions (got {count})"

    # 3. Verify that each question contains concrete, non-empty text, intent, and answers
    for ev in evaluations:
        assert ev.question_id.startswith("Q-")
        assert len(ev.generated_question) > 10
        assert resolved_entity.name.lower() in ev.generated_question.lower() or "acme" in ev.generated_question.lower()
        assert ev.answerability_status in ["ANSWERABLE", "PARTIAL", "UNANSWERABLE", "EVIDENCE_GAP", "CONFLICTING"]
        assert ev.crawled_answer is not None and len(ev.crawled_answer) > 5
        assert ev.recommended_answer is not None and len(ev.recommended_answer) > 5
        assert 1 <= ev.citability_score <= 10
        # Phase 1: Verify serialized telemetry fields are populated
        assert ev.grounding_ratio is not None
        assert ev.answer_risk in ["LOW", "MEDIUM", "HIGH"]
        assert ev.retrieval_evidence_count is not None

    # 4. Verify that pricing and identity questions find answers from the evidence
    identity_eval = next(e for e in evaluations if "core commercial solution" in e.generated_question.lower() or "what exactly is" in e.generated_question.lower())
    assert identity_eval.is_answerable is True
    assert identity_eval.answerability_status in ["ANSWERABLE", "PARTIAL"]
    assert identity_eval.evidence_snippet is not None
    assert identity_eval.citability_score >= 5

    pricing_eval = next(e for e in evaluations if "starting price" in e.generated_question.lower() or "how much" in e.generated_question.lower() or "entry-level" in e.generated_question.lower())
    assert pricing_eval.is_answerable is True
    assert "$" in pricing_eval.crawled_answer or "99" in pricing_eval.crawled_answer or pricing_eval.evidence_snippet is not None


@pytest.mark.asyncio
async def test_dynamic_sandbox_correctly_identifies_unanswerable_gaps():
    # Setup thin site with NO pricing and NO security certifications
    pages = [
        PageEvidence(
            url="https://mysterious-agency.com/",
            title="Mysterious Agency | Design Firm",
            h1=["We Make Things Look Beautiful"],
            body_text="We craft creative campaigns for ambitious companies. Let's work together.",
            word_count=35
        )
    ]

    resolved_entity = UniversalEntityResolver.resolve_from_evidence(
        website_url="https://mysterious-agency.com",
        pages=pages
    )

    sandbox = DynamicQuestionSandboxEngine()
    evaluations = await sandbox.generate_and_evaluate_100_questions(
        pages=pages,
        website_url="https://mysterious-agency.com",
        resolved_entity=resolved_entity
    )

    assert len(evaluations) == 100

    # Locate pricing questions - must be flagged as UNANSWERABLE / EVIDENCE_GAP
    pricing_q = next(e for e in evaluations if "starting price" in e.generated_question.lower())
    assert pricing_q.is_answerable is False
    assert pricing_q.answerability_status in ["UNANSWERABLE", "EVIDENCE_GAP"]
    assert "not disclosed" in pricing_q.crawled_answer.lower() or "not available" in pricing_q.crawled_answer.lower() or "not published" in pricing_q.crawled_answer.lower()
    assert pricing_q.gap_analysis is not None
    assert pricing_q.citability_score <= 3
    assert pricing_q.projected_patch_gain > 0.40
    assert pricing_q.grounding_ratio == 0.0
    assert pricing_q.answer_risk == "HIGH"
