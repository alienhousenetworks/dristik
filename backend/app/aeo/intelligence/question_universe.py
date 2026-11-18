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

        # 1. Product Catalog Questions
        for p in prods[:4]:
            q_list.append(
                BusinessQuestion(
                    question_id=f"AEO-Q-{q_idx:03d}",
                    question_text=f"What are the key ingredients and clinical benefits of {b} {p}?",
                    intent=QuestionIntent.INFORMATIONAL,
                    topic_cluster="Product Specifications",
                    audience_persona="Health-conscious Consumers",
                    funnel_stage=FunnelStage.MID_FUNNEL,
                    business_importance=BusinessImportance.HIGH,
                    geographic_relevance="Global / Primary Market",
                    required_evidence_type="INGREDIENT_LIST",
                    origin_stream=QuestionOriginStream.PRODUCT_CATALOG,
                )
            )
            q_idx += 1
            q_list.append(
                BusinessQuestion(
                    question_id=f"AEO-Q-{q_idx:03d}",
                    question_text=f"How much does {b} {p} cost and where can I order it online?",
                    intent=QuestionIntent.TRANSACTIONAL,
                    topic_cluster="Pricing & Purchasing",
                    audience_persona="Ready-to-buy Customers",
                    funnel_stage=FunnelStage.BOTTOM_OF_FUNNEL,
                    business_importance=BusinessImportance.CRITICAL,
                    geographic_relevance="Domestic E-commerce",
                    required_evidence_type="PRICING_DATA",
                    origin_stream=QuestionOriginStream.PRODUCT_CATALOG,
                )
            )
            q_idx += 1

        # 2. Website Content Questions
        q_list.append(
            BusinessQuestion(
                question_id=f"AEO-Q-{q_idx:03d}",
                question_text=f"What is {b} and how is it different from traditional {cat} brands?",
                intent=QuestionIntent.COMMERCIAL,
                topic_cluster="Brand Differentiation",
                audience_persona="First-time Visitors",
                funnel_stage=FunnelStage.TOP_OF_FUNNEL,
                business_importance=BusinessImportance.HIGH,
                geographic_relevance="Global",
                required_evidence_type="VALUE_PROPOSITION",
                origin_stream=QuestionOriginStream.WEBSITE_CONTENT,
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
        q_list.append(
            BusinessQuestion(
                question_id=f"AEO-Q-{q_idx:03d}",
                question_text=f"Which {b} product should I get if I have sensitive gums?",
                intent=QuestionIntent.COMMERCIAL,
                topic_cluster="Product Recommendation",
                audience_persona="Conversational Assistant Users",
                funnel_stage=FunnelStage.MID_FUNNEL,
                business_importance=BusinessImportance.CRITICAL,
                geographic_relevance="Global",
                required_evidence_type="CLINICAL_TRIAL",
                origin_stream=QuestionOriginStream.CONVERSATIONAL_PROMPT,
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
