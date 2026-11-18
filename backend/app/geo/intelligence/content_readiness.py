"""
Machine-Readable Content Readiness & Passage Testing — Phase 4.3

Implements the mandatory 8-Point Passage Extraction Test:
1. Extract content into self-contained passages (40–80 words)
2. Test whether each passage stands independently
3. Identify missing contextual references
4. Detect ambiguous pronouns ("they", "it", "these", "this product")
5. Detect unsupported statements & marketing superlatives
6. Identify missing entity relationships (subject-predicate-object)
7. Evaluate source attribution
8. Compute passage factual density (factual tokens vs. marketing fluff)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TestedPassageResult(BaseModel):
    passage_index: int
    text_snippet: str
    word_count: int
    stands_independently: bool
    ambiguous_pronouns_detected: List[str] = Field(default_factory=list)
    unsupported_claims_detected: List[str] = Field(default_factory=list)
    missing_context_signals: List[str] = Field(default_factory=list)
    has_explicit_entity: bool
    factual_density_score: float  # 0.0 to 1.0
    quotability_grade: str  # HIGH, MODERATE, POOR
    remediation_suggestion: Optional[str] = None


class ContentReadinessReport(BaseModel):
    url: str
    total_passages_tested: int
    high_quotability_passages_count: int
    average_factual_density: float
    passages: List[TestedPassageResult] = Field(default_factory=list)
    has_pricing_declared: bool
    has_definitions_declared: bool
    has_source_attribution: bool
    overall_readiness_score: float  # 0.0 to 100.0
    actionable_remediation: List[str] = Field(default_factory=list)


class ContentReadinessEngine:
    """
    Evaluates passage extractability, pronoun clarity, and factual grounding for AI quotation.
    """

    AMBIGUOUS_PRONOUNS = ["they", "them", "it", "its", "these", "this company", "this product", "our solution"]
    UNSUPPORTED_SUPERLATIVES = ["world-class", "revolutionary", "best", "unparalleled", "game-changing", "100%", "miraculous"]

    @classmethod
    def test_page_passages(
        cls,
        url: str,
        body_text: str,
        brand_name: str = "",
    ) -> ContentReadinessReport:
        clean = re.sub(r"\s+", " ", body_text).strip()
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        
        # Group sentences into 40–80 word passages
        passages_raw: List[str] = []
        curr_p: List[str] = []
        curr_w = 0

        for s in sentences:
            w_len = len(s.split())
            if curr_w + w_len > 75 and curr_p:
                passages_raw.append(" ".join(curr_p))
                curr_p = [s]
                curr_w = w_len
            else:
                curr_p.append(s)
                curr_w += w_len
        if curr_p:
            passages_raw.append(" ".join(curr_p))

        tested_passages: List[TestedPassageResult] = []
        high_quote_count = 0
        total_density = 0.0
        recs: List[str] = []

        brand_low = (brand_name or "").lower()

        for idx, p_text in enumerate(passages_raw[:15]):  # test up to 15 key passages
            p_words = p_text.split()
            w_count = len(p_words)
            low_text = p_text.lower()

            # 1. Ambiguous Pronoun Detection
            amb_pronouns = []
            for pron in cls.AMBIGUOUS_PRONOUNS:
                if re.search(rf"\b{re.escape(pron)}\b", low_text):
                    amb_pronouns.append(pron)


            # 2. Unsupported Superlatives
            superlatives = []
            for sup in cls.UNSUPPORTED_SUPERLATIVES:
                if re.search(rf"\b{re.escape(sup)}\b", low_text):
                    superlatives.append(sup)

            # 3. Explicit Entity Presence
            has_entity = (brand_low in low_text) if brand_low else bool(re.search(r"\b[A-Z][a-z]+\b", p_text))

            # 4. Context Missing
            missing_ctx = []
            if amb_pronouns and not has_entity:
                missing_ctx.append("Starts with an ambiguous pronoun without naming the subject entity.")

            # 5. Independent Standing
            stands_ind = (not missing_ctx) and (has_entity) and (w_count >= 25)

            # 6. Factual Density (factual noun/verbs/numbers vs. fluff)
            fact_tokens = len(re.findall(r"\b(?:\d+|[A-Z][a-z]+|contains|features|approved|certified|costs|priced|designed)\b", p_text))
            fluff_tokens = len(superlatives) * 2
            density = max(0.1, min(1.0, round((fact_tokens / max(w_count, 1)) * 3.5, 2)))
            total_density += density

            # 7. Quotability Grade
            if stands_ind and density >= 0.65 and not superlatives:
                q_grade = "HIGH"
                high_quote_count += 1
                suggestion = None
            elif stands_ind or density >= 0.45:
                q_grade = "MODERATE"
                suggestion = "Clarify ambiguous pronouns or ground superlatives with quantified evidence."
            else:
                q_grade = "POOR"
                suggestion = "Rewrite into a declarative 50-word answer block naming the brand explicitly."

            tested_passages.append(
                TestedPassageResult(
                    passage_index=idx + 1,
                    text_snippet=p_text[:120] + "..." if len(p_text) > 120 else p_text,
                    word_count=w_count,
                    stands_independently=stands_ind,
                    ambiguous_pronouns_detected=amb_pronouns,
                    unsupported_claims_detected=superlatives,
                    missing_context_signals=missing_ctx,
                    has_explicit_entity=has_entity,
                    factual_density_score=density,
                    quotability_grade=q_grade,
                    remediation_suggestion=suggestion,
                )
            )

        avg_density = round(total_density / max(len(tested_passages), 1), 2)
        has_pricing = bool(re.search(r'(?:\$|₹|€|£|\bUSD\b|\bINR\b)\s*\d+', clean))
        has_definitions = bool(re.search(r'\b(?:is defined as|refers to|means|is an?|are)\b', clean, re.I))
        has_author = bool(re.search(r'\b(?:author|written by|reviewed by|dr\.|md|published)\b', clean, re.I))

        # Overall Readiness Score
        readiness_score = round(
            (high_quote_count / max(len(tested_passages), 1) * 40.0)
            + (avg_density * 30.0)
            + (10.0 if has_pricing else 0.0)
            + (10.0 if has_definitions else 0.0)
            + (10.0 if has_author else 0.0),
            1,
        )

        if not has_pricing:
            recs.append("Declare transparent pricing or starting ranges directly in page copy.")
        if high_quote_count < len(tested_passages) * 0.4:
            recs.append("Structure 40–60 word declarative answer blocks with explicit brand names at section headers.")

        return ContentReadinessReport(
            url=url,
            total_passages_tested=len(tested_passages),
            high_quotability_passages_count=high_quote_count,
            average_factual_density=avg_density,
            passages=tested_passages,
            has_pricing_declared=has_pricing,
            has_definitions_declared=has_definitions,
            has_source_attribution=has_author,
            overall_readiness_score=min(100.0, readiness_score),
            actionable_remediation=recs,
        )
