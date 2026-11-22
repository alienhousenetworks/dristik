"""
Test Suite — Phase 5: Answer Engine Optimization (AEO) Intelligence (10/10 Transformation)

Verifies all 10 sub-phases:
- 5.1: Question Universe Generation (Multi-stream business-tailored questions)
- 5.2: Question-to-Page Graph & Anomaly Detection (Unanswered, partial, competing pages)
- 5.3: Answer Completeness Engine (Required element checklists, partial tracking)
- 5.4: Passage Extractability Evidence (Granular passage hashes, definition syntax, density)
- 5.5: Multi-Agent Factual Grounding (Deterministic catalog checks, cross-page contradictions)
- 5.6: Live Answer Evaluation (Direct answer cards, brand accuracy, citation correctness)
- 5.7: Conversational Voice Optimization (Spoken 20–40 word blocks, VOICE_SURFACE_UNTESTED disclosure)
- 5.8: Third-Party Answer Credibility (Claim-to-source graph, unsupported claim isolation)
- 5.9: Decoupled 10-Dimension Scorecard (Track A 75% vs Track B 25% decoupled scoring firewall)
- 5.10: AEO Remediation Lifecycle (Answer drafting, FAQ schema patches, re-test verification)
"""
import pytest
from app.aeo.intelligence.question_universe import (
    QuestionUniverseGenerator,
    QuestionUniverseReport,
    QuestionIntent,
    FunnelStage,
    QuestionOriginStream,
)
from app.aeo.intelligence.question_page_graph import (
    QuestionPageGraphEngine,
    QuestionPageGraphReport,
    CoverageStatus,
    MappingAnomalyType,
)
from app.aeo.intelligence.answer_completeness import (
    AnswerCompletenessEngine,
    EvaluatedAnswerCompleteness,
)
from app.aeo.intelligence.passage_extractability import (
    PassageExtractabilityEngine,
    PassageExtractabilityReport,
)
from app.aeo.intelligence.factual_grounding_pipeline import (
    FactualGroundingPipeline,
    FactualGroundingPipelineReport,
)
from app.aeo.intelligence.live_answer_evaluation import (
    LiveAnswerEvaluationEngine,
    LiveAnswerEvaluationReport,
)
from app.aeo.intelligence.conversational_voice import (
    ConversationalVoiceEngine,
    ConversationalVoiceReport,
)
from app.aeo.intelligence.third_party_credibility import (
    ThirdPartyCredibilityEngine,
    ClaimToSourceGraphReport,
)
from app.aeo.intelligence.aeo_scorecard import (
    AeoScorecardEngine,
    AeoScorecardReport,
)
from app.aeo.intelligence.aeo_remediation import (
    AeoRemediationEngine,
    AeoRemediationReport,
    RemediationTaskStatus,
)


# ============================================================================
# Phase 5.1: Question Universe Generation
# ============================================================================

def test_phase5_1_question_universe_generation():
    products = ["Smart Sonic Toothbrush", "Probiotics Mouthwash"]
    faqs = [{"question": "Are Perfora products vegan and cruelty-free?"}]
    gsc = ["perfora sonic brush price"]
    support = ["How do I claim a warranty replacement?"]

    report: QuestionUniverseReport = QuestionUniverseGenerator.generate_universe(
        domain="perfora.co",
        brand_name="Perfora",
        category="oral care products",
        products=products,
        faq_items=faqs,
        gsc_queries=gsc,
        support_tickets=support,
    )

    assert report.total_questions_generated >= 8
    # Verify multi-stream origins
    streams = set(report.stream_breakdown.keys())
    assert QuestionOriginStream.PRODUCT_CATALOG.value in streams
    assert QuestionOriginStream.WEBSITE_CONTENT.value in streams
    assert QuestionOriginStream.FAQ_SECTION.value in streams
    assert QuestionOriginStream.SEARCH_CONSOLE.value in streams
    assert QuestionOriginStream.CUSTOMER_SUPPORT.value in streams

    # Check question classification
    q_first = report.questions[0]
    assert q_first.funnel_stage in (FunnelStage.TOP_OF_FUNNEL, FunnelStage.MID_FUNNEL, FunnelStage.BOTTOM_OF_FUNNEL)
    assert q_first.required_evidence_type is not None


# ============================================================================
# Phase 5.2: Question-to-Page Graph & Anomaly Detection
# ============================================================================

def test_phase5_2_question_page_graph_and_anomalies():
    universe = QuestionUniverseGenerator.generate_universe(
        domain="perfora.co",
        brand_name="Perfora",
        category="oral care products",
        products=["Smart Sonic Toothbrush"],
    )

    crawled_pages = [
        {
            "url": "https://perfora.co/products/sonic-brush",
            "title": "Smart Sonic Toothbrush by Perfora",
            "body_text": "Features dentist-approved bristles and 2-minute timer. Clinically validated oral care.",
        },
        {
            "url": "https://perfora.co/brush-alternative",
            "title": "Smart Sonic Toothbrush by Perfora",
            "body_text": "Features dentist-approved bristles and 2-minute timer. Clinically validated oral care.",
        },
    ]

    graph_report: QuestionPageGraphReport = QuestionPageGraphEngine.build_graph(
        questions=universe.questions,
        crawled_pages=crawled_pages,
    )

    assert graph_report.total_questions > 0
    # Competing pages detected
    assert len(graph_report.competing_pages_detected) >= 1
    # Unanswered queries isolated
    assert graph_report.unanswered_count > 0
    unans_node = next(n for n in graph_report.nodes if n.coverage_status == CoverageStatus.UNANSWERED)
    assert MappingAnomalyType.UNANSWERED_QUESTION in unans_node.detected_anomalies


# ============================================================================
# Phase 5.3: Answer Completeness Engine (Checklists)
# ============================================================================

def test_phase5_3_answer_completeness_checklists():
    # 1. Partial Answer (Mentions product and active ingredients, but lacks warnings and concentrations)
    partial_passage = (
        "Perfora Probiotics Mouthwash contains natural essential oils, green tea extract, and probiotics. "
        "It provides refreshing breath for 12 hours."
    )
    res_partial: EvaluatedAnswerCompleteness = AnswerCompletenessEngine.evaluate_passage_completeness(
        question_id="Q-ING-001",
        question_text="What ingredients are in Perfora Probiotics Mouthwash and are there any warnings?",
        target_url="https://perfora.co/mouthwash",
        passage_text=partial_passage,
    )
    assert res_partial.answer_status == "PARTIAL"
    assert any("Warning" in m for m in res_partial.missing_elements)

    # 2. Complete Pricing Answer
    complete_pricing = (
        "Perfora Sonic Electric Toothbrush costs $29 USD per unit, available as a one-time purchase or quarterly brush head subscription. "
        "All domestic orders include free standard shipping and are backed by an unconditional 30-day money-back guarantee."
    )
    res_complete: EvaluatedAnswerCompleteness = AnswerCompletenessEngine.evaluate_passage_completeness(
        question_id="Q-PRC-001",
        question_text="How much does Perfora Sonic Toothbrush cost and what is the return policy?",
        target_url="https://perfora.co/products/brush",
        passage_text=complete_pricing,
    )
    assert res_complete.answer_status == "COMPLETE"
    assert res_complete.completeness_score_pct >= 80.0
    assert len(res_complete.missing_elements) == 0


# ============================================================================
# Phase 5.4: Passage Extractability Evidence
# ============================================================================

def test_phase5_4_passage_extractability_evidence():
    html = """
    <h2>What is Perfora Sonic Technology?</h2>
    <p>Perfora Sonic Technology refers to high-frequency 26,000 micro-vibrations per minute that gently clean interdental spaces. Developed with leading clinical dentists in 2024, the device delivers 42 percent greater plaque reduction than manual brushing.</p>
    <h2>Customer Reviews</h2>
    <p>They are totally amazing and I love them so much.</p>
    """

    report: PassageExtractabilityReport = PassageExtractabilityEngine.analyze_page_extractability(
        url="https://perfora.co/technology",
        html=html,
    )

    assert report.total_passages_analyzed >= 2
    # Verify direct answer passage identified
    p_direct = report.passages[0]
    assert p_direct.is_self_contained is True
    assert p_direct.has_explicit_definition is True
    assert p_direct.extractability_grade == "A_DIRECT_ANSWER"

    # Verify ambiguous second passage flagged
    p_ambig = report.passages[1]
    assert p_ambig.is_self_contained is False
    assert p_ambig.extractability_grade in ("C_AMBIGUOUS", "D_UNEXTRACTABLE")


# ============================================================================
# Phase 5.5: Multi-Agent Factual Grounding & Contradictions
# ============================================================================

def test_phase5_5_factual_grounding_and_contradictions():
    claims = [
        "Perfora Smart Toothbrush costs $29.00 USD.",
        "Perfora Smart Toothbrush costs $49.00 USD.",  # Conflicting claim
        "Features clinically validated tartar control.",
    ]
    catalog = {
        "price": 29.00,
        "products": ["Smart Toothbrush", "Probiotics Mouthwash"],
    }
    pages_map = {
        "https://perfora.co/products/brush": "Free shipping above $50 on all orders.",
        "https://perfora.co/checkout": "Free shipping above $75 for domestic orders.",
    }

    report: FactualGroundingPipelineReport = FactualGroundingPipeline.run_grounding_pipeline(
        claims=claims,
        empirical_catalog=catalog,
        pages_content_map=pages_map,
    )

    assert report.grounded_claims_count >= 1
    # Check discrepancy on $49 price claim
    fnd_bad_price = next(v for v in report.validations if "$49" in v.claim_text)
    assert fnd_bad_price.is_factually_grounded is False
    assert "contradicts" in fnd_bad_price.discrepancy_note

    # Check cross-page contradiction detected
    assert len(report.contradictions_detected) == 1
    assert report.contradictions_detected[0].topic == "Free Shipping Threshold"


# ============================================================================
# Phase 5.6: Live Answer Evaluation
# ============================================================================

def test_phase5_6_live_answer_evaluation():
    tested_queries = [
        {
            "question_id": "Q-01",
            "question": "What is the cost of Perfora electric toothbrush?",
            "surface": "ChatGPT Search",
            "response": "Perfora electric toothbrush is priced at $29 with sonic vibrations and replacement heads.",
            "citations": ["https://perfora.co/products/brush"],
        },
        {
            "question_id": "Q-02",
            "question": "Who makes the best sonic toothbrush?",
            "surface": "Perplexity",
            "response": "Top recommendations include Oral-B and Philips Sonicare.",
            "citations": ["https://oralb.com", "https://philips.com"],
        },
    ]

    report: LiveAnswerEvaluationReport = LiveAnswerEvaluationEngine.evaluate_live_answers(
        domain="perfora.co",
        brand_name="Perfora",
        tested_queries=tested_queries,
        expected_facts={"cost": "$29"},
    )

    assert report.total_questions_tested == 2
    assert report.direct_answer_rate_pct == 100.0
    assert report.citation_correctness_rate_pct == 50.0  # 1 out of 2 cited first-party canonical
    # Oral-B detected as competitor in Q-02
    assert "Oral-B" in report.results[1].competitors_present_in_answer


# ============================================================================
# Phase 5.7: Conversational & Voice Optimization
# ============================================================================

def test_phase5_7_conversational_voice_readiness():
    text = (
        "Perfora is a modern oral wellness brand designed by clinical dentists. "
        "Our sonic electric toothbrushes use gentle micro-vibrations to protect gums while removing plaque effectively. "
        "Visit https://perfora.co/complex-catalog-item-id-129381283?session=9283921 for terms."
    )

    report: ConversationalVoiceReport = ConversationalVoiceEngine.audit_conversational_readiness(
        url="https://perfora.co/about",
        html_or_text=text,
        is_live_audio_tested=False,
    )

    assert report.conversational_readiness_score > 0
    # Guardrail: Voice surface untested disclosure
    assert report.voice_surface_tested is False
    assert report.voice_testing_status == "VOICE_SURFACE_UNTESTED"
    assert "not tested on physical hardware" in report.testing_statement


# ============================================================================
# Phase 5.8: Third-Party Answer Credibility & Claim Graph
# ============================================================================

def test_phase5_8_third_party_credibility_graph():
    claims = [
        "Endorsed by the Indian Dental Association for gum safety.",
        "Clinically proven 99% cavity prevention within 30 days.",
    ]
    external_sources = [
        {
            "name": "Indian Dental Association",
            "type": "CERTIFICATION",
            "tier": "TIER_1_OFFICIAL_ACCREDITATION",
            "url": "https://ida.org.in/certifications",
        }
    ]

    report: ClaimToSourceGraphReport = ThirdPartyCredibilityEngine.build_credibility_graph(
        claims=claims,
        external_sources=external_sources,
    )

    assert report.total_claims_mapped == 2
    assert report.supported_claims_count == 1
    assert report.unsupported_claims_count == 1
    # Check unsupported claim flagged
    unsupported_edge = next(e for e in report.edges if not e.is_supported)
    assert "99% cavity" in unsupported_edge.claim_text
    assert unsupported_edge.evidence_strength == "UNSUPPORTED"


# ============================================================================
# Phase 5.9: Decoupled 10-Dimension AEO Scorecard
# ============================================================================

def test_phase5_9_aeo_scorecard_decoupled():
    # Test 1: Track A measured, Track B untested
    scores = {
        "question_coverage": 85.0,
        "answer_completeness": 80.0,
        "passage_extractability": 75.0,
        "factual_grounding": 90.0,
        "structured_readiness": 80.0,
        "conversational_coverage": 70.0,
        "source_credibility": 75.0,
        "live_answer_appearance": None,
        "citation_accuracy": None,
        "answer_consistency": None,
    }

    card_untested: AeoScorecardReport = AeoScorecardEngine.calculate_scorecard(
        dimension_scores=scores,
        live_testing_ran=False,
    )

    assert card_untested.assessment_status == "PARTIAL_ASSESSMENT"
    assert card_untested.coverage_percentage == 75.0
    assert card_untested.is_live_tested is False
    assert card_untested.overall_score is None
    assert card_untested.track_a_readiness_score is not None
    assert card_untested.track_b_live_score is None
    assert "Track B Live Answer Outcomes are NOT_TESTED" in card_untested.firewall_disclosure_statement
    assert "overall grade is withheld" in card_untested.firewall_disclosure_statement

    # Test 2: Both Track A and Track B measured
    scores_full = dict(scores)
    scores_full.update({
        "live_answer_appearance": 85.0,
        "citation_accuracy": 80.0,
        "answer_consistency": 90.0,
    })

    card_full: AeoScorecardReport = AeoScorecardEngine.calculate_scorecard(
        dimension_scores=scores_full,
        live_testing_ran=True,
    )

    assert card_full.assessment_status == "FULL_ASSESSMENT"
    assert card_full.coverage_percentage == 100.0
    assert card_full.track_b_live_score == 84.0


# ============================================================================
# Phase 5.10: AEO Remediation Lifecycle & Re-Test
# ============================================================================

def test_phase5_10_aeo_remediation_lifecycle():
    unanswered = [
        {
            "id": "AEO-Q-099",
            "question": "What is the return policy for Perfora electric toothbrush?",
            "category": "Purchase Policies",
            "target_url": "https://perfora.co/returns",
        }
    ]

    report: AeoRemediationReport = AeoRemediationEngine.generate_remediation_plan(
        domain="perfora.co",
        brand_name="Perfora",
        unanswered_questions=unanswered,
    )

    assert report.total_remediations_generated == 1
    proposal = report.proposals[0]
    assert proposal.status == RemediationTaskStatus.PROPOSED
    assert "30-day money-back guarantee" in proposal.drafted_answer_block
    assert "FAQPage" in proposal.recommended_faq_schema_patch or "Question" in proposal.recommended_faq_schema_patch

    # Simulate post-fix re-test
    updated_page_text = "Return policy: Perfora offers an unconditional 30-day money-back guarantee on all electric toothbrushes."
    verified_proposal = AeoRemediationEngine.verify_retest(proposal, updated_page_text)
    assert verified_proposal.status == RemediationTaskStatus.VERIFIED_FIXED
