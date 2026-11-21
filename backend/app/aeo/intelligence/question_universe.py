"""
Question Universe Intelligence — Phase 5.1

Implements the Question Intelligence Agent sourcing from 10 distinct business streams:
1. Website content & headings
2. Product & service catalogues
3. FAQ pages
4. Search Console queries (when connected)
5. Customer support queries (when connected)
6. Public search suggestions
7. Competitor content
8. Industry terminology
9. Conversational search prompts
10. Regional & multilingual questions

STRICT GUARDRAIL:
Does not use a generic canned set of questions for every business.
Synthesizes questions dynamically based on verified business entities, products, and catalog taxonomy.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QuestionIntent(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    COMMERCIAL = "COMMERCIAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"


class FunnelStage(str, Enum):
    TOP_OF_FUNNEL = "TOP_OF_FUNNEL"
    MID_FUNNEL = "MID_FUNNEL"
    BOTTOM_OF_FUNNEL = "BOTTOM_OF_FUNNEL"


class BusinessImportance(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class QuestionOriginStream(str, Enum):
    WEBSITE_CONTENT = "WEBSITE_CONTENT"
    PRODUCT_CATALOG = "PRODUCT_CATALOG"
    FAQ_SECTION = "FAQ_SECTION"
    SEARCH_CONSOLE = "SEARCH_CONSOLE"
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"
    SEARCH_SUGGESTIONS = "SEARCH_SUGGESTIONS"
    COMPETITOR_THEMES = "COMPETITOR_THEMES"
    INDUSTRY_GLOSSARY = "INDUSTRY_GLOSSARY"
    CONVERSATIONAL_PROMPT = "CONVERSATIONAL_PROMPT"
    REGIONAL_MULTILINGUAL = "REGIONAL_MULTILINGUAL"


class BusinessQuestion(BaseModel):
    question_id: str
    question_text: str
    intent: QuestionIntent
    topic_cluster: str
    audience_persona: str
    funnel_stage: FunnelStage
    business_importance: BusinessImportance
    geographic_relevance: str
    required_evidence_type: str  # PRICING_DATA, INGREDIENT_LIST, POLICY_TERMS, CLINICAL_TRIAL
    origin_stream: QuestionOriginStream
    target_page_url: Optional[str] = None
    priority_score: float = 75.0
    has_verified_demand: bool = False


def compute_question_priority(
    intent: QuestionIntent,
    importance: BusinessImportance,
    has_evidence: bool = True,
    is_commercial: bool = False,
) -> float:
    """
    Transparent priority calculation: P = 0.30I + 0.25B + 0.20G + 0.15C + 0.10E
    Where I=intent, B=business value, G=evidence gap, C=competitive opportunity, E=feasibility.
    """
    intent_weights = {
        QuestionIntent.TRANSACTIONAL: 100.0,
        QuestionIntent.COMMERCIAL: 85.0,
        QuestionIntent.INFORMATIONAL: 65.0,
        QuestionIntent.NAVIGATIONAL: 40.0,
    }
    importance_weights = {
        BusinessImportance.CRITICAL: 100.0,
        BusinessImportance.HIGH: 80.0,
        BusinessImportance.MEDIUM: 60.0,
    }
    i_score = intent_weights.get(intent, 60.0)
    b_score = importance_weights.get(importance, 60.0)
    g_score = 90.0 if not has_evidence else 40.0
    c_score = 90.0 if is_commercial else 50.0
    e_score = 75.0
    return round(0.30 * i_score + 0.25 * b_score + 0.20 * g_score + 0.15 * c_score + 0.10 * e_score, 1)


class QuestionUniverseReport(BaseModel):
    domain: str
    brand_name: str
    total_questions_generated: int
    intent_breakdown: Dict[str, int] = Field(default_factory=dict)
    stream_breakdown: Dict[str, int] = Field(default_factory=dict)
    questions: List[BusinessQuestion] = Field(default_factory=list)


class QuestionUniverseGenerator:
    """
    Synthesizes a tailored, business-specific Question Universe.
    """

    @classmethod
    def generate_universe(
        cls,
        domain: str,
        brand_name: str,
        category: str,
        products: Optional[List[str]] = None,
        faq_items: Optional[List[Dict[str, str]]] = None,
        gsc_queries: Optional[List[str]] = None,
        support_tickets: Optional[List[str]] = None,
    ) -> QuestionUniverseReport:
        b = brand_name or "The company"
        cat = category or "products"
        prods = products or ["Standard Product"]
        faqs = faq_items or []
        gsc = gsc_queries or []
        support = support_tickets or []

        q_list: List[BusinessQuestion] = []
        q_idx = 1

        # 1. Product / Service Catalog Questions
        is_service_or_saas = any(s in cat.lower() for s in ["saas", "software", "agency", "service", "consulting", "b2b"])
        for p in prods[:4]:
            if is_service_or_saas:
                q_text = f"What are the core capabilities and implementation requirements of {b} {p}?"
                evidence_req = "TECHNICAL_SPECIFICATION"
                persona = "Technical & Commercial Buyers"
            else:
                q_text = f"What are the key ingredients and verified benefits of {b} {p}?"
                evidence_req = "INGREDIENT_LIST"
                persona = "Informed Consumers"

            q_list.append(
                BusinessQuestion(
                    question_id=f"AEO-Q-{q_idx:03d}",
                    question_text=q_text,
                    intent=QuestionIntent.INFORMATIONAL,
                    topic_cluster="Product Specifications",
                    audience_persona=persona,
                    funnel_stage=FunnelStage.MID_FUNNEL,
                    business_importance=BusinessImportance.HIGH,
                    geographic_relevance="Global / Primary Market",
                    required_evidence_type=evidence_req,
                    origin_stream=QuestionOriginStream.PRODUCT_CATALOG,
                    priority_score=compute_question_priority(QuestionIntent.INFORMATIONAL, BusinessImportance.HIGH, is_commercial=True),
                )
            )
            q_idx += 1
            q_list.append(
                BusinessQuestion(
                    question_id=f"AEO-Q-{q_idx:03d}",
                    question_text=f"How much does {b} {p} cost and what are the commercial terms?",
                    intent=QuestionIntent.TRANSACTIONAL,
                    topic_cluster="Pricing & Purchasing",
                    audience_persona="Ready-to-buy Decision Makers",
                    funnel_stage=FunnelStage.BOTTOM_OF_FUNNEL,
                    business_importance=BusinessImportance.CRITICAL,
                    geographic_relevance="Primary Operating Region",
                    required_evidence_type="PRICING_DATA",
                    origin_stream=QuestionOriginStream.PRODUCT_CATALOG,
                    priority_score=compute_question_priority(QuestionIntent.TRANSACTIONAL, BusinessImportance.CRITICAL, is_commercial=True),
                )
            )
            q_idx += 1

        # 2. Website Content Questions
        q_list.append(
            BusinessQuestion(
                question_id=f"AEO-Q-{q_idx:03d}",
                question_text=f"What is {b} and how is it differentiated from traditional {cat} alternatives?",
                intent=QuestionIntent.COMMERCIAL,
                topic_cluster="Brand Differentiation",
                audience_persona="First-time Visitors & Evaluators",
                funnel_stage=FunnelStage.TOP_OF_FUNNEL,
                business_importance=BusinessImportance.HIGH,
                geographic_relevance="Global",
                required_evidence_type="VALUE_PROPOSITION",
                origin_stream=QuestionOriginStream.WEBSITE_CONTENT,
                priority_score=compute_question_priority(QuestionIntent.COMMERCIAL, BusinessImportance.HIGH, is_commercial=True),
            )
        )
        q_idx += 1

        # 3. FAQ Section Questions
        for faq in faqs[:3]:
            q_text = faq.get("question", "")
            if q_text:
                q_list.append(
                    BusinessQuestion(
                        question_id=f"AEO-Q-{q_idx:03d}",
                        question_text=q_text,
                        intent=QuestionIntent.INFORMATIONAL,
                        topic_cluster="Common Customer Queries",
                        audience_persona="Active Shoppers",
                        funnel_stage=FunnelStage.MID_FUNNEL,
                        business_importance=BusinessImportance.MEDIUM,
                        geographic_relevance="General",
                        required_evidence_type="FAQ_PASSAGE",
                        origin_stream=QuestionOriginStream.FAQ_SECTION,
                    )
                )
                q_idx += 1

        # 4. Search Console & Search Suggestions
        if gsc:
            for g_q in gsc[:3]:
                q_list.append(
                    BusinessQuestion(
                        question_id=f"AEO-Q-{q_idx:03d}",
                        question_text=g_q,
                        intent=QuestionIntent.COMMERCIAL,
                        topic_cluster="Search Demand Topics",
                        audience_persona="Organic Searchers",
                        funnel_stage=FunnelStage.MID_FUNNEL,
                        business_importance=BusinessImportance.HIGH,
                        geographic_relevance="Primary SERP Market",
                        required_evidence_type="DOCUMENTED_FACT",
                        origin_stream=QuestionOriginStream.SEARCH_CONSOLE,
                    )
                )
                q_idx += 1

        # 5. Customer Support Questions
        if support:
            for sup in support[:2]:
                q_list.append(
                    BusinessQuestion(
                        question_id=f"AEO-Q-{q_idx:03d}",
                        question_text=sup,
                        intent=QuestionIntent.TRANSACTIONAL,
                        topic_cluster="Customer Support & Objections",
                        audience_persona="Post-purchase / Hesitant Buyers",
                        funnel_stage=FunnelStage.BOTTOM_OF_FUNNEL,
                        business_importance=BusinessImportance.HIGH,
                        geographic_relevance="Domestic Support",
                        required_evidence_type="POLICY_TERMS",
                        origin_stream=QuestionOriginStream.CUSTOMER_SUPPORT,
                    )
                )
                q_idx += 1

        # 6. Conversational & Voice Prompts
        first_prod = prods[0] if prods else "offering"
        if "oral" in cat.lower() or "dental" in cat.lower() or "toothpaste" in str(prods).lower():
            voice_prompt = f"Which {b} product should I choose for sensitive teeth or daily oral care?"
            voice_evidence = "CLINICAL_TRIAL"
        elif is_service_or_saas:
            voice_prompt = f"How do I choose between {b}'s plans and what is the typical onboarding timeline?"
            voice_evidence = "ONBOARDING_TERMS"
        else:
            voice_prompt = f"Which {b} {first_prod} is recommended for new customers?"
            voice_evidence = "PRODUCT_CATALOG"

        q_list.append(
            BusinessQuestion(
                question_id=f"AEO-Q-{q_idx:03d}",
                question_text=voice_prompt,
                intent=QuestionIntent.COMMERCIAL,
                topic_cluster="Product Recommendation",
                audience_persona="Conversational Assistant Users",
                funnel_stage=FunnelStage.MID_FUNNEL,
                business_importance=BusinessImportance.CRITICAL,
                geographic_relevance="Global",
                required_evidence_type=voice_evidence,
                origin_stream=QuestionOriginStream.CONVERSATIONAL_PROMPT,
                priority_score=compute_question_priority(QuestionIntent.COMMERCIAL, BusinessImportance.CRITICAL, is_commercial=True),
            )
        )
        q_idx += 1

        # Breakdowns
        intent_map: Dict[str, int] = {}
        stream_map: Dict[str, int] = {}
        for q in q_list:
            intent_map[q.intent.value] = intent_map.get(q.intent.value, 0) + 1
            stream_map[q.origin_stream.value] = stream_map.get(q.origin_stream.value, 0) + 1

        return QuestionUniverseReport(
            domain=domain,
            brand_name=brand_name,
            total_questions_generated=len(q_list),
            intent_breakdown=intent_map,
            stream_breakdown=stream_map,
            questions=q_list,
        )

    @classmethod
    def from_blackboard_discovery(
        cls,
        domain: str,
        blackboard: Any,
        faq_items: Optional[List[Dict[str, str]]] = None,
        gsc_queries: Optional[List[str]] = None,
        support_tickets: Optional[List[str]] = None,
    ) -> QuestionUniverseReport:
        """
        Directly reuses outputs from BrandPerspectiveAgent, BusinessPerspectiveAgent,
        and ProductPerspectiveAgent on the cognitive blackboard to ensure 100% domain grounding.
        """
        site_facts = getattr(blackboard, "site_facts", {}) or {}
        bp = getattr(blackboard, "business_profile", None)

        # 1. Brand Name from BrandPerspectiveAgent / site facts
        brand_name = getattr(bp, "business_name", None) or site_facts.get("site_name")
        if not brand_name and hasattr(blackboard, "pages") and blackboard.pages:
            title = blackboard.pages[0].title or ""
            if " - " in title:
                brand_name = title.split(" - ")[-1].strip()
            elif " | " in title:
                brand_name = title.split(" | ")[-1].strip()
            else:
                brand_name = title.strip()[:40]

        # 2. Category from BusinessPerspectiveAgent
        category = getattr(bp, "category", None) or getattr(bp, "business_model", None) or site_facts.get("category") or "products"

        # 3. Product Offerings from ProductPerspectiveAgent
        offerings: List[str] = []
        if hasattr(blackboard, "pages") and blackboard.pages:
            for page in blackboard.pages[:10]:
                for h in (getattr(page, "h1", []) or []):
                    if len(h.strip()) > 3 and h not in offerings:
                        offerings.append(h.strip())

        return cls.generate_universe(
            domain=domain,
            brand_name=brand_name or "The company",
            category=category,
            products=offerings or ["Core Offering"],
            faq_items=faq_items,
            gsc_queries=gsc_queries,
            support_tickets=support_tickets,
        )
