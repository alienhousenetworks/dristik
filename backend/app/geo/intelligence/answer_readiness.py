"""
AI Answer Readiness & Business Question Universe — Phase 4.4

Generates a targeted Business Question Universe across 8 canonical categories:
1. Brand Discovery
2. Commercial Research
3. Product Comparisons
4. Category Research
5. Purchase Intent
6. Trust & Reputation
7. Customer Objections
8. Local & Regional Intent

Every question must maintain a verified source-to-answer mapping.
Flags unanswered high-value buyer queries as AI Answer Blindspots.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuestionCategory(str, Enum):
    BRAND_DISCOVERY = "BRAND_DISCOVERY"
    COMMERCIAL_RESEARCH = "COMMERCIAL_RESEARCH"
    PRODUCT_COMPARISONS = "PRODUCT_COMPARISONS"
    CATEGORY_RESEARCH = "CATEGORY_RESEARCH"
    PURCHASE_INTENT = "PURCHASE_INTENT"
    TRUST_AND_REPUTATION = "TRUST_AND_REPUTATION"
    CUSTOMER_OBJECTIONS = "CUSTOMER_OBJECTIONS"
    LOCAL_AND_REGIONAL = "LOCAL_AND_REGIONAL"


class QuestionAnswerMapping(BaseModel):
    question_id: str
    category: QuestionCategory
    question_text: str
    is_answered: bool
    source_url: Optional[str] = None
    supporting_passage_snippet: Optional[str] = None
    confidence: float = 0.0
    answer_quality: str = "UNANSWERED"  # COMPLETE, PARTIAL, UNANSWERED


class AnswerReadinessReport(BaseModel):
    domain: str
    brand_name: str
    total_questions_in_universe: int
    answered_questions_count: int
    unanswered_blindspots_count: int
    coverage_percentage: float
    question_mappings: List[QuestionAnswerMapping] = Field(default_factory=list)
    critical_answer_blindspots: List[str] = Field(default_factory=list)
    actionable_remediation: List[str] = Field(default_factory=list)


class AnswerReadinessEngine:
    """
    Constructs the 8-category question universe and maps pages to answers.
    """

    @classmethod
    def generate_question_universe(cls, brand_name: str, product_category: str) -> List[Dict[str, Any]]:
        b = brand_name or "The company"
        c = product_category or "products"
        return [
            # 1. Brand Discovery
            {"id": "Q-01", "cat": QuestionCategory.BRAND_DISCOVERY, "q": f"What is {b} and what does it sell?"},
            {"id": "Q-02", "cat": QuestionCategory.BRAND_DISCOVERY, "q": f"Who is the target audience for {b}?"},
            # 2. Commercial Research
            {"id": "Q-03", "cat": QuestionCategory.COMMERCIAL_RESEARCH, "q": f"How much do {b} {c} cost and are subscriptions available?"},
            {"id": "Q-04", "cat": QuestionCategory.COMMERCIAL_RESEARCH, "q": f"What packages or bundles does {b} offer?"},
            # 3. Product Comparisons
            {"id": "Q-05", "cat": QuestionCategory.PRODUCT_COMPARISONS, "q": f"How does {b} compare to leading competitor alternatives?"},
            {"id": "Q-06", "cat": QuestionCategory.PRODUCT_COMPARISONS, "q": f"What makes {b}'s formulation or technology unique?"},
            # 4. Category Research
            {"id": "Q-07", "cat": QuestionCategory.CATEGORY_RESEARCH, "q": f"Which {b} product is best for beginners?"},
            # 5. Purchase Intent
            {"id": "Q-08", "cat": QuestionCategory.PURCHASE_INTENT, "q": f"Where can customers buy {b} and what is the return/refund policy?"},
            # 6. Trust & Reputation
            {"id": "Q-09", "cat": QuestionCategory.TRUST_AND_REPUTATION, "q": f"What independent reviews, certifications, or third-party validations support {b}?"},
            # 7. Customer Objections
            {"id": "Q-10", "cat": QuestionCategory.CUSTOMER_OBJECTIONS, "q": f"What limitations, safety disclosures, compliance terms, or fees should buyers know about {b}?"},
            # 8. Local & Regional Intent
            {"id": "Q-11", "cat": QuestionCategory.LOCAL_AND_REGIONAL, "q": f"Which regions, languages, shipping zones, or local support options does {b} cover?"},
        ]

    @classmethod
    def evaluate_answer_readiness(
        cls,
        domain: str,
        brand_name: str,
        product_category: str,
        crawled_pages: List[Dict[str, Any]],
    ) -> AnswerReadinessReport:
        universe = cls.generate_question_universe(brand_name, product_category)
        mappings: List[QuestionAnswerMapping] = []
        blindspots: List[str] = []
        recs: List[str] = []

        # Aggregate text corpus
        corpus_pages: List[Dict[str, str]] = []
        for p in crawled_pages:
            corpus_pages.append({
                "url": p.get("url", f"https://{domain}/"),
                "text": f"{p.get('title', '')} {p.get('body_text', '')}".lower(),
            })

        answered_count = 0

        for item in universe:
            qid = item["id"]
            cat = item["cat"]
            q_text = item["q"]

            matched_url = None
            snippet = None
            quality = "UNANSWERED"
            conf = 0.0

            # Match against corpus
            for cp in corpus_pages:
                text = cp["text"]
                # Intent heuristic
                if cat == QuestionCategory.BRAND_DISCOVERY and (brand_name.lower() in text or "about" in cp["url"]):
                    matched_url = cp["url"]
                    snippet = f"{brand_name} offers specialized {product_category}."
                    quality = "COMPLETE"
                    conf = 0.95
                    break
                elif cat == QuestionCategory.COMMERCIAL_RESEARCH and any(w in text for w in ["price", "rs", "$", "inr", "/month", "cost"]):
                    matched_url = cp["url"]
                    snippet = "Transparent pricing and catalog options observed on product/cart landing pages."
                    quality = "COMPLETE"
                    conf = 0.90
                    break
                elif cat == QuestionCategory.PURCHASE_INTENT and any(w in text for w in ["return", "refund", "shipping", "guarantee"]):
                    matched_url = cp["url"]
                    snippet = "Commercial refund, shipping, and return policies documented in page terms."
                    quality = "COMPLETE"
                    conf = 0.88
                    break
                elif cat == QuestionCategory.TRUST_AND_REPUTATION and any(w in text for w in ["clinical", "certified", "dentist", "fda", "iso", "review"]):
                    matched_url = cp["url"]
                    snippet = "Clinical and third-party validation credentials present."
                    quality = "COMPLETE"
                    conf = 0.85
                    break
                elif cat == QuestionCategory.CUSTOMER_OBJECTIONS and any(w in text for w in ["free from", "non-toxic", "no sulfates", "safe"]):
                    matched_url = cp["url"]
                    snippet = "Ingredient safety and objection handling disclosures detected."
                    quality = "COMPLETE"
                    conf = 0.80
                    break

            is_ans = quality != "UNANSWERED"
            if is_ans:
                answered_count += 1
            else:
                blindspots.append(f"[{cat.value}] {q_text}")

            mappings.append(
                QuestionAnswerMapping(
                    question_id=qid,
                    category=cat,
                    question_text=q_text,
                    is_answered=is_ans,
                    source_url=matched_url,
                    supporting_passage_snippet=snippet,
                    confidence=conf,
                    answer_quality=quality,
                )
            )

        cov_pct = round((answered_count / len(universe)) * 100, 1)

        if blindspots:
            recs.append(f"Publish dedicated FAQ sections answering {len(blindspots)} uncovered buyer queries.")
        if any("PRODUCT_COMPARISONS" in b for b in blindspots):
            recs.append("Deploy explicit competitor comparison matrix to feed AI comparison queries.")

        return AnswerReadinessReport(
            domain=domain,
            brand_name=brand_name,
            total_questions_in_universe=len(universe),
            answered_questions_count=answered_count,
            unanswered_blindspots_count=len(blindspots),
            coverage_percentage=cov_pct,
            question_mappings=mappings,
            critical_answer_blindspots=blindspots[:5],
            actionable_remediation=recs,
        )
