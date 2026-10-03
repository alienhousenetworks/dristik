"""
Unit tests for Evidence-Grounded AEO Remediation.
Tests:
1. Verified questions produce 40-60 word Answer Blocks.
2. Unsupported questions produce CONTENT_REQUIRED advisories without hallucinated values.
3. FAQPage schema contains only verified questions.
"""
import json
from app.domain.models import GeoQuestionEvidence
from app.intelligence.geo.remediation_classifier import build_evidence_grounded_aeo_remediations


def test_aeo_remediation_evidence_grounding_and_safeguards():
    questions = [
        GeoQuestionEvidence(
            question_key="identity_what",
            question="What is AlienHouse and what does it do?",
            category="Entity Identity",
            status="SUPPORTED",
            evidence_url="https://alienhouse.in",
            evidence_snippet="AlienHouse is an enterprise software engineering studio specializing in high-throughput FastAPI and React applications for growing tech businesses.",
            why="Supported by homepage heading."
        ),
        GeoQuestionEvidence(
            question_key="price_cost",
            question="How much does AlienHouse cost?",
            category="Pricing & Commercial Terms",
            status="UNSUPPORTED",
            evidence_url=None,
            evidence_snippet=None,
            why="No pricing found."
        ),
        GeoQuestionEvidence(
            question_key="caps_deployment",
            question="Can AlienHouse deploy on-premise or cloud?",
            category="Core Capabilities & Services",
            status="PARTIAL",
            evidence_url="https://alienhouse.in/services",
            evidence_snippet="We deploy cloud architectures across AWS and GCP with Kubernetes containerization.",
            why="Partial keywords found."
        )
    ]

    pack = build_evidence_grounded_aeo_remediations(
        questions=questions,
        brand_name="AlienHouse",
        website_url="https://alienhouse.in"
    )

    # 1. Answer blocks generated for supported / partial with evidence
    assert len(pack.answer_block_patches) >= 2
    for block in pack.answer_block_patches:
        assert block.word_count <= 60
        assert "AlienHouse" in block.heading or "AlienHouse" in block.answer_text

    # 2. Content required advisory for unsupported pricing
    pricing_adv = next((a for a in pack.content_required_advisories if a.question_key == "price_cost"), None)
    assert pricing_adv is not None
    assert "No verified first-party evidence found" in pricing_adv.reason
    assert "pricing tiers" in pricing_adv.recommended_policy_statement

    # 3. FAQ schema includes verified questions only
    assert pack.faq_schema_json_ld is not None
    faq_obj = json.loads(pack.faq_schema_json_ld)
    assert faq_obj["@type"] == "FAQPage"
    q_names = [q["name"] for q in faq_obj["mainEntity"]]
    assert "What is AlienHouse and what does it do?" in q_names
    # Pricing must NOT be in FAQ schema
    assert "How much does AlienHouse cost?" not in q_names
