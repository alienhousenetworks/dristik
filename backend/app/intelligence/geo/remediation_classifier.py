"""
Dristik Evidence-Grounded AEO Remediation & FAQ Safeguard Engine.
Implements:
1. Evidence-Constrained Answer Blocks (40-60 words using ONLY verified first-party evidence).
2. FAQ Schema Safeguard (Classifies questions before generating FAQPage JSON-LD; never generates schema for unverified facts).
3. CONTENT_REQUIRED Advisories (Flags missing commercial policies without hallucinating values).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.models import GeoQuestionEvidence, CanonicalEntityFact


class AnswerBlockPatch(BaseModel):
    question_key: str
    question: str
    heading: str
    answer_text: str
    word_count: int
    source_url: Optional[str] = None
    evidence_grounding: str
    action: str = "Insert 40-60 word definition block directly under H2 question heading."


class ContentRequiredAdvisory(BaseModel):
    question_key: str
    question: str
    category: str
    reason: str
    recommended_policy_statement: str


class AeoRemediationPack(BaseModel):
    brand_name: str
    target_domain: str
    total_evaluated: int
    answer_block_patches: List[AnswerBlockPatch] = Field(default_factory=list)
    faq_schema_json_ld: Optional[str] = None
    faq_schema_question_count: int = 0
    content_required_advisories: List[ContentRequiredAdvisory] = Field(default_factory=list)
    internal_link_recommendations: List[Dict[str, str]] = Field(default_factory=list)


def build_evidence_grounded_aeo_remediations(
    questions: List[GeoQuestionEvidence],
    brand_name: str,
    website_url: str,
    canonical_facts: Optional[List[CanonicalEntityFact]] = None
) -> AeoRemediationPack:
    clean_domain = website_url.replace("https://", "").replace("http://", "").split("/")[0]
    brand = brand_name or clean_domain.split(".")[0].capitalize()

    answer_blocks: List[AnswerBlockPatch] = []
    content_advisories: List[ContentRequiredAdvisory] = []
    internal_links: List[Dict[str, str]] = []
    valid_faq_pairs: List[Dict[str, str]] = []

    for q in questions:
        q_key = q.question_key
        q_text = q.question
        cat = q.category
        status = q.status
        snippet = (q.evidence_snippet or q.answer_snippet or "").strip()
        url = q.evidence_url or website_url

        # Safeguard 1: Answer blocks generated ONLY when first-party evidence actually exists
        if status in ("SUPPORTED", "PARTIAL") and snippet and len(snippet.split()) >= 6:
            # Format concise 40-60 word inverted-pyramid answer
            words = snippet.split()
            core_words = words[:55]
            synthesized_answer = " ".join(core_words)
            if not synthesized_answer.endswith("."):
                synthesized_answer += "."

            ans_block = AnswerBlockPatch(
                question_key=q_key,
                question=q_text,
                heading=f"<h2>{q_text}</h2>",
                answer_text=synthesized_answer,
                word_count=len(core_words),
                source_url=url,
                evidence_grounding=f"Grounded in verified crawl excerpt from {url}",
                action="Insert 40-60 word definition block directly beneath H2 question heading for direct engine synthesis."
            )
            answer_blocks.append(ans_block)

            # Safeguard 2: Include in FAQPage schema ONLY if question has verified answer
            if status == "SUPPORTED" and cat not in ("Pricing & Commercial Terms"):
                valid_faq_pairs.append({
                    "question": q_text,
                    "answer": synthesized_answer
                })

        elif q.remediation_type == "INTERNAL_LINK":
            internal_links.append({
                "question": q_text,
                "recommendation": f"Keywords for '{q_text}' exist on secondary pages. Add anchor-linked reference from the primary page to consolidate entity context."
            })

        else:
            # Safeguard 3: NEVER invent claims for missing data; issue CONTENT_REQUIRED advisory
            policy_rec = {
                "Pricing & Commercial Terms": f"Publish transparent pricing tiers, starting rates, or commercial licensing terms for {brand} to eliminate 'Contact sales' displacement.",
                "Security, Trust & Compliance": f"Publish verified security standards (SOC 2, ISO 27001, GDPR compliance, or data encryption guarantees) for {brand}.",
                "Comparative & Differentiators": f"Publish an objective comparison table specifying how {brand} differs from primary category alternatives.",
                "Implementation & Onboarding": f"Publish concrete implementation milestones, typical onboarding timelines, and technical prerequisites.",
            }.get(cat, f"Publish verified first-party answers to '{q_text}' to secure answer engine citations.")

            content_advisories.append(ContentRequiredAdvisory(
                question_key=q_key,
                question=q_text,
                category=cat,
                reason="No verified first-party evidence found on crawled pages. AI content generation blocked to prevent hallucination.",
                recommended_policy_statement=policy_rec
            ))

    # Build validated FAQPage JSON-LD snippet
    faq_schema_str = None
    if valid_faq_pairs:
        faq_data = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": pair["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": pair["answer"]
                    }
                }
                for pair in valid_faq_pairs[:12]  # Cap at top 12 verified pairs to prevent schema bloating
            ]
        }
        faq_schema_str = json.dumps(faq_data, indent=2)

    return AeoRemediationPack(
        brand_name=brand,
        target_domain=clean_domain,
        total_evaluated=len(questions),
        answer_block_patches=answer_blocks,
        faq_schema_json_ld=faq_schema_str,
        faq_schema_question_count=len(valid_faq_pairs[:12]),
        content_required_advisories=content_advisories,
        internal_link_recommendations=internal_links,
    )
