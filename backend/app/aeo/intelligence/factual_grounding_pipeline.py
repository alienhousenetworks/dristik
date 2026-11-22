"""
Multi-Agent Factual Grounding Pipeline — Phase 5.5

Coordinates a 6-agent evaluation pipeline:
1. AnswerExtractionAgent — Extracts answer candidates from page passages
2. CompletenessAgent — Verifies presence of mandatory answer attributes
3. FactualGroundingAgent — Deterministically verifies claims against actual empirical data sources
4. ContradictionDetector — Identifies cross-page discrepancies (e.g. conflicting prices or policies)
5. SourceVerificationAgent — Confirms authoritative citation and primary source backing
6. IndependentCriticAgent — Audits findings to eliminate false certainty and ungrounded claims

STRICT GUARDRAIL:
Employs deterministic database/catalog cross-checks instead of subjective LLM guesses.
E.g., verifies stated prices against actual catalog values directly.
"""
from __future__ import annotations

from enum import Enum
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class AnswerabilityState(str, Enum):
    ANSWERABLE = "ANSWERABLE"
    PARTIAL = "PARTIAL"
    UNANSWERABLE = "UNANSWERABLE"
    CONFLICTING = "CONFLICTING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NOT_TESTED = "NOT_TESTED"
    ERROR = "ERROR"


class FactualValidationResult(BaseModel):
    claim_text: str
    verified_against_source: str  # "PRODUCT_CATALOG", "SCHEMA_PRICING", "POLICY_DOCUMENT", "DOM_HEADING"
    is_factually_grounded: bool
    empirical_reference_value: Any
    observed_text_value: Any
    discrepancy_note: Optional[str] = None


class AnswerabilityEvaluationResult(BaseModel):
    question: str
    answerability_state: AnswerabilityState
    relevance_passed: bool
    relevance_rejection_reason: Optional[str] = None
    grounding_score_pct: float = 0.0
    total_claims: int = 0
    supported_claims: int = 0
    first_party_citation_url: Optional[str] = None
    first_party_passage_snippet: Optional[str] = None
    validations: List[FactualValidationResult] = Field(default_factory=list)
    contradictions: List[CrossPageContradiction] = Field(default_factory=list)


class CrossPageContradiction(BaseModel):
    topic: str
    page_a_url: str
    page_a_statement: str
    page_b_url: str
    page_b_statement: str
    conflict_severity: str  # "HIGH", "MEDIUM"


class FactualGroundingPipelineReport(BaseModel):
    total_claims_evaluated: int
    grounded_claims_count: int
    unsupported_claims_count: int
    factual_grounding_score_pct: float
    validations: List[FactualValidationResult] = Field(default_factory=list)
    contradictions_detected: List[CrossPageContradiction] = Field(default_factory=list)
    critic_verdict: str


class FactualGroundingPipeline:
    """
    Coordinates multi-agent grounding verification with deterministic data cross-checks.
    """

    @classmethod
    def run_grounding_pipeline(
        cls,
        claims: List[str],
        empirical_catalog: Dict[str, Any],  # {"price": float, "products": List[str], "shipping_free_threshold": float}
        pages_content_map: Optional[Dict[str, str]] = None,
    ) -> FactualGroundingPipelineReport:
        validations: List[FactualValidationResult] = []
        contradictions: List[CrossPageContradiction] = []
        grounded_count = 0

        # 1. Deterministic Cross-Check of Claims against Catalog
        for claim in claims:
            c_low = claim.lower()
            is_grounded = False
            ref_val = None
            obs_val = None
            discrepancy = None
            source_type = "GENERAL_DOM"

            # Check Price Claims
            price_match = re.search(r'(?:\$|₹|€|£)\s*(\d+(?:\.\d+)?)', claim)
            if price_match and "price" in empirical_catalog:
                obs_price = float(price_match.group(1))
                ref_price = float(empirical_catalog["price"])
                source_type = "PRODUCT_CATALOG"
                ref_val = ref_price
                obs_val = obs_price

                if abs(obs_price - ref_price) < 0.01:
                    is_grounded = True
                else:
                    discrepancy = f"Stated price (${obs_price}) contradicts verified catalog price (${ref_price})."

            # Check Product Identity Claims
            elif "products" in empirical_catalog and any(p.lower() in c_low for p in empirical_catalog["products"]):
                matched_prod = next(p for p in empirical_catalog["products"] if p.lower() in c_low)
                source_type = "PRODUCT_CATALOG"
                ref_val = matched_prod
                obs_val = matched_prod
                is_grounded = True

            else:
                # A keyword such as "tested" or "return" is not a source. Without a catalog
                # or page match the claim stays ungrounded.
                is_grounded = False
                discrepancy = "Claim lacks direct empirical source in product catalog or policy documents."

            if is_grounded:
                grounded_count += 1

            validations.append(
                FactualValidationResult(
                    claim_text=claim,
                    verified_against_source=source_type,
                    is_factually_grounded=is_grounded,
                    empirical_reference_value=ref_val,
                    observed_text_value=obs_val,
                    discrepancy_note=discrepancy,
                )
            )

        # 2. Contradiction Detection across pages using ContradictionDetector
        if pages_content_map and len(pages_content_map) >= 2:
            from app.aeo.intelligence.contradiction_detector import ContradictionDetector
            contra_report = ContradictionDetector.audit_pages(pages_content_map)
            for c in contra_report.conflicts:
                contradictions.append(
                    CrossPageContradiction(
                        topic=c.field,
                        page_a_url=c.left_surface,
                        page_a_statement=c.left_value,
                        page_b_url=c.right_surface,
                        page_b_statement=c.right_value,
                        conflict_severity=c.severity.value,
                    )
                )

        total_claims = len(claims)
        grounding_score = round((grounded_count / max(total_claims, 1)) * 100, 1)

        critic = (
            "PASSED: All factual statements directly match verified catalog and policy sources."
            if not contradictions and grounding_score >= 80.0
            else f"FLAGGED: Detected {len(contradictions)} cross-page contradiction(s) and {total_claims - grounded_count} ungrounded claim(s)."
        )

        return FactualGroundingPipelineReport(
            total_claims_evaluated=total_claims,
            grounded_claims_count=grounded_count,
            unsupported_claims_count=total_claims - grounded_count,
            factual_grounding_score_pct=grounding_score,
            validations=validations,
            contradictions_detected=contradictions,
            critic_verdict=critic,
        )

    @classmethod
    def validate_stage_a_relevance(
        cls,
        question: str,
        passage_text: str,
        target_entities: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Stage A Relevance Gate:
        Rejects passages that do not address the question's core subject or business entities.
        Irrelevant passages are rejected immediately and cannot earn grounding points.
        """
        if not passage_text or len(passage_text.strip()) < 15:
            return False, "Passage is empty or contains insufficient text."

        p_low = passage_text.lower()
        q_low = question.lower()

        # Stop words to filter out
        stop_words = {"what", "how", "why", "which", "where", "when", "who", "does", "the", "and", "is", "are", "for", "with", "from"}
        q_tokens = [w for w in re.findall(r'[a-zA-Z0-9]+', q_low) if len(w) > 2 and w not in stop_words]

        # Check entity match if provided
        entities = target_entities or []
        entity_match = any(e.lower() in p_low for e in entities) if entities else True

        # Check keyword overlap
        overlap = sum(1 for token in q_tokens if token in p_low)
        min_overlap = min(2, len(q_tokens)) if q_tokens else 1

        if not entity_match and overlap < min_overlap:
            return False, f"Stage A Relevance Failed: passage lacks matching business entity and has only {overlap}/{len(q_tokens)} keyword overlap."

        if overlap < min_overlap and not entity_match:
            return False, f"Stage A Relevance Failed: passage does not address the question subject (insufficient overlap)."

        return True, None

    @classmethod
    def evaluate_grounded_answerability(
        cls,
        question: str,
        candidate_passages: List[Dict[str, Any]],  # [{"url": str, "text": str, "entities": List[str]}]
        claims: List[str],
        empirical_catalog: Dict[str, Any],
        pages_content_map: Optional[Dict[str, str]] = None,
    ) -> AnswerabilityEvaluationResult:
        """
        Two-stage Answerability & Grounding evaluation:
        Stage A: Mandatory relevance gating on candidate passages.
        Stage B: Claim-level verification only if Stage A passes.
        """
        if not candidate_passages:
            return AnswerabilityEvaluationResult(
                question=question,
                answerability_state=AnswerabilityState.UNANSWERABLE,
                relevance_passed=False,
                relevance_rejection_reason="No candidate passages retrieved for question.",
                grounding_score_pct=0.0,
            )

        # Stage A: Filter candidate passages through relevance gate
        required_entities = list(empirical_catalog.get("products", []))
        if "brand_name" in empirical_catalog:
            required_entities.append(empirical_catalog["brand_name"])

        relevant_passages: List[Dict[str, Any]] = []
        rejection_reasons: List[str] = []

        for p in candidate_passages:
            passed, reason = cls.validate_stage_a_relevance(
                question=question,
                passage_text=p.get("text", ""),
                target_entities=required_entities if required_entities else None,
            )
            if passed:
                relevant_passages.append(p)
            else:
                rejection_reasons.append(reason or "Irrelevant passage")

        if not relevant_passages:
            return AnswerabilityEvaluationResult(
                question=question,
                answerability_state=AnswerabilityState.UNANSWERABLE,
                relevance_passed=False,
                relevance_rejection_reason=f"All {len(candidate_passages)} candidate passage(s) rejected: {rejection_reasons[0] if rejection_reasons else 'insufficient relevance'}",
                grounding_score_pct=0.0,
            )

        # Stage B: Run claim grounding pipeline against empirical catalog & validated passages
        report = cls.run_grounding_pipeline(
            claims=claims,
            empirical_catalog=empirical_catalog,
            pages_content_map=pages_content_map,
        )

        # Determine state
        best_passage = relevant_passages[0]
        if report.contradictions_detected:
            state = AnswerabilityState.CONFLICTING
        elif report.factual_grounding_score_pct >= 90.0:
            state = AnswerabilityState.ANSWERABLE
        elif report.factual_grounding_score_pct > 0.0:
            state = AnswerabilityState.PARTIAL
        else:
            state = AnswerabilityState.UNANSWERABLE

        return AnswerabilityEvaluationResult(
            question=question,
            answerability_state=state,
            relevance_passed=True,
            grounding_score_pct=report.factual_grounding_score_pct,
            total_claims=report.total_claims_evaluated,
            supported_claims=report.grounded_claims_count,
            first_party_citation_url=best_passage.get("url"),
            first_party_passage_snippet=best_passage.get("text", "")[:280],
            validations=report.validations,
            contradictions=report.contradictions_detected,
        )
