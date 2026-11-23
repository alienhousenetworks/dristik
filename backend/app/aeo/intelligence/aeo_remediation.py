"""
AEO Remediation Lifecycle & Re-Test Engine — Phase 5.10

Manages the complete lifecycle for unanswered or partial questions:
1. Information gap diagnosis
2. Destination page assignment
3. Structured answer drafting (50-word declarative blocks)
4. Schema recommendations (FAQPage JSON-LD)
5. Source material requirements
6. Pre/post remediation re-test verification
"""
from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RemediationTaskStatus(str, Enum):
    PROPOSED = "PROPOSED"
    IN_PROGRESS = "IN_PROGRESS"
    CONTENT_DRAFTED = "CONTENT_DRAFTED"
    VERIFIED_FIXED = "VERIFIED_FIXED"
    STILL_UNANSWERED = "STILL_UNANSWERED"


class AeoRemediationProposal(BaseModel):
    proposal_id: str
    question_id: str
    question_text: str
    target_destination_url: str
    information_gap_summary: str
    required_answer_structure: str
    drafted_answer_block: str
    recommended_faq_schema_patch: str
    source_material_needed: str
    status: RemediationTaskStatus = RemediationTaskStatus.PROPOSED


class AeoRemediationReport(BaseModel):
    domain: str
    total_remediations_generated: int
    proposals: List[AeoRemediationProposal] = Field(default_factory=list)
    retested_questions_count: int = 0
    resolved_questions_count: int = 0


class AeoRemediationEngine:
    """
    Generates structured remediation proposals and verifies re-tested question resolutions.
    """

    @classmethod
    def generate_remediation_plan(
        cls,
        domain: str,
        brand_name: str,
        unanswered_questions: List[Dict[str, Any]],  # {"id": str, "question": str, "category": str, "target_url": Optional[str]}
        brand_facts: Optional[Dict[str, Any]] = None,
    ) -> AeoRemediationReport:
        proposals: List[AeoRemediationProposal] = []
        facts = brand_facts or {}

        for idx, item in enumerate(unanswered_questions):
            qid = item.get("id", f"AEO-Q-{idx + 1:03d}")
            q_text = item.get("question", "")
            cat = item.get("category", "General")
            target_url = item.get("target_url") or f"https://{domain}/faq"
            q_low = q_text.lower()

            # Resolve grounded fact from supplied brand_facts; never fabricate guarantees or clinical claims.
            grounded_fact: Optional[str] = None
            for fk, fv in facts.items():
                if not fv:
                    continue
                fk_norm = fk.lower().replace("_", " ")
                if fk_norm in q_low or any(tok in q_low for tok in fk_norm.split() if len(tok) > 3):
                    grounded_fact = str(fv).strip()
                    break

            if grounded_fact:
                answer_body = f"{brand_name}: {grounded_fact} Official reference: https://{domain}."
                schema_answer_text = answer_body
            else:
                answer_body = (
                    f"[CONFIRM_WITH_BRAND_FACTS: Provide a verified 40-60 word declarative answer for "
                    f"'{q_text}' on {brand_name} ({cat}) with exact figures/policy terms from {domain}.]"
                )
                schema_answer_text = (
                    f"[CONFIRM_WITH_BRAND_FACTS: Verified answer for '{q_text}' must match visible HTML copy on {domain}.]"
                )

            # 1. Direct-answer section block (visible static HTML; never hidden behind JS-only accordions)
            draft_text = (
                f"<section class=\"direct-answer\" data-question-id=\"{qid}\">\n"
                f"  <h2>{q_text}</h2>\n"
                f"  <p>{answer_body}</p>\n"
                f"</section>"
            )

            # 2. Optional Question JSON-LD patch (only valid when visible HTML matches verbatim)
            schema_patch = {
                "@context": "https://schema.org",
                "@type": "Question",
                "name": q_text,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": schema_answer_text,
                },
            }

            proposals.append(
                AeoRemediationProposal(
                    proposal_id=f"AEO-REM-{idx + 1:03d}",
                    question_id=qid,
                    question_text=q_text,
                    target_destination_url=target_url,
                    information_gap_summary=f"No direct declarative passage answering '{q_text}' was found on the site.",
                    required_answer_structure="Visible static H2 question header + 40–60 word grounded declarative answer block with explicit subject naming and verifiable evidence.",
                    drafted_answer_block=draft_text,
                    recommended_faq_schema_patch=json.dumps(schema_patch, indent=2),
                    source_material_needed="Verified first-party brand facts, specifications, or published policy terms.",
                    status=RemediationTaskStatus.PROPOSED,
                )
            )

        return AeoRemediationReport(
            domain=domain,
            total_remediations_generated=len(proposals),
            proposals=proposals,
        )

    @classmethod
    def verify_retest(
        cls,
        proposal: AeoRemediationProposal,
        crawled_page_text: str,
    ) -> AeoRemediationProposal:
        # Check if the page now contains keywords from question
        q_words = [w for w in proposal.question_text.lower().split() if len(w) > 3]
        matches = sum(1 for w in q_words if w in crawled_page_text.lower())
        
        if matches >= max(2, len(q_words) // 2):
            proposal.status = RemediationTaskStatus.VERIFIED_FIXED
        else:
            proposal.status = RemediationTaskStatus.STILL_UNANSWERED
        return proposal
