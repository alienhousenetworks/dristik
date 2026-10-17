"""
Dristik AI Search Intent Graph
Maps buyer problem-solving paths:
User Problem -> Search Query -> Intent -> Topic -> Website Page -> Answer -> CTA -> Conversion.
Identifies broken commercial acquisition paths and lost opportunities.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.domain.models import PageEvidence, BusinessProfile

class IntentPath(BaseModel):
    path_id: str
    user_problem: str
    search_query: str
    intent_type: str  # Informational, Commercial, Transactional, Comparison
    target_topic: str
    matched_page_url: Optional[str] = None
    has_direct_answer: bool = False
    has_visible_cta: bool = False
    status: str = "HEALTHY"  # HEALTHY, BROKEN_NO_PAGE, BROKEN_NO_ANSWER, BROKEN_NO_CTA
    revenue_risk: str = "LOW"  # CRITICAL, HIGH, MEDIUM, LOW

class SearchIntentGraph:
    """
    Constructs and audits buyer search intent pathways.
    """

    def construct_intent_paths(
        self,
        business_profile: BusinessProfile,
        pages: List[PageEvidence]
    ) -> List[IntentPath]:
        paths: List[IntentPath] = []
        name = business_profile.business_name
        niche = business_profile.niche
        crawled_urls = [p.url.lower() for p in pages]

        # 1. Commercial Intent: Pricing & Plans
        pricing_page = next((p.url for p in pages if "pricing" in p.url.lower()), None)
        paths.append(IntentPath(
            path_id="intent_01_pricing",
            user_problem="How much does this solution cost and what features are included?",
            search_query=f"{name} pricing and plans",
            intent_type="Commercial",
            target_topic="Pricing Tiers & Licensing",
            matched_page_url=pricing_page,
            has_direct_answer=pricing_page is not None,
            has_visible_cta=bool(business_profile.primary_cta),
            status="HEALTHY" if pricing_page else "BROKEN_NO_PAGE",
            revenue_risk="CRITICAL" if not pricing_page else "LOW"
        ))

        # 2. Informational Intent: Core Solution Capabilities
        product_page = next((p.url for p in pages if any(k in p.url.lower() for k in ["features", "product", "solutions"])), None)
        paths.append(IntentPath(
            path_id="intent_02_product",
            user_problem="What capabilities does this software provide for workflow automation?",
            search_query=f"best {niche} tools for enterprise",
            intent_type="Informational",
            target_topic="Core Product Architecture",
            matched_page_url=product_page,
            has_direct_answer=product_page is not None,
            has_visible_cta=bool(business_profile.primary_cta),
            status="HEALTHY" if product_page else "BROKEN_NO_ANSWER",
            revenue_risk="HIGH" if not product_page else "LOW"
        ))

        # 3. Comparison Intent: Alternatives & Moat
        comparison_page = next((p.url for p in pages if any(k in p.url.lower() for k in ["vs", "compare", "alternative", "comparison"])), None)
        paths.append(IntentPath(
            path_id="intent_03_comparison",
            user_problem="Why should I choose this brand over existing market alternatives?",
            search_query=f"{name} alternatives vs competitors",
            intent_type="Comparison",
            target_topic="Competitive Differentiation",
            matched_page_url=comparison_page,
            has_direct_answer=comparison_page is not None,
            has_visible_cta=bool(business_profile.primary_cta) if comparison_page else False,
            status="HEALTHY" if comparison_page else "BROKEN_NO_PAGE",
            revenue_risk="HIGH" if not comparison_page else "LOW"
        ))

        return paths
