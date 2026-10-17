"""
Dristik AI Evidence Acquisition Planner (Active Investigation)
Determines what missing evidence would most effectively reduce uncertainty during an audit.
Prioritizes targeted pages for secondary crawl passes.
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.domain.models import PageEvidence, BusinessProfile

class AcquisitionTarget(BaseModel):
    target_type: str  # page, schema, selector
    url_pattern: str
    rationale: str
    expected_uncertainty_reduction: float  # 0.0 - 1.0
    priority: int = 1

class EvidenceAcquisitionPlanner:
    """
    Active investigator: inspects working state and selects targeted assets to acquire.
    """

    def plan_next_acquisitions(
        self,
        crawled_pages: List[PageEvidence],
        business_profile: BusinessProfile,
        discovered_urls: List[str]
    ) -> List[AcquisitionTarget]:
        targets: List[AcquisitionTarget] = []
        crawled_urls_set = {p.url.lower().rstrip("/") for p in crawled_pages}

        # 1. Uncertainty: ICP or commercial pricing model is unclear
        if business_profile.value_proposition == "Value proposition not clearly stated." or not business_profile.primary_cta:
            pricing_candidates = [u for u in discovered_urls if any(k in u.lower() for k in ["pricing", "plans", "cost"])]
            for u in pricing_candidates[:2]:
                if u.lower().rstrip("/") not in crawled_urls_set:
                    targets.append(AcquisitionTarget(
                        target_type="page",
                        url_pattern=u,
                        rationale="Clarifies commercial pricing tiers, ICP, and primary conversion action.",
                        expected_uncertainty_reduction=0.35,
                        priority=1
                    ))

        # 2. Uncertainty: Proof & Trust Credentials
        about_candidates = [u for u in discovered_urls if any(k in u.lower() for k in ["about", "company", "team", "security"])]
        for u in about_candidates[:2]:
            if u.lower().rstrip("/") not in crawled_urls_set:
                targets.append(AcquisitionTarget(
                    target_type="page",
                    url_pattern=u,
                    rationale="Acquires corporate entity backing, leadership credentials, and compliance signals.",
                    expected_uncertainty_reduction=0.25,
                    priority=2
                ))

        # 3. Product & Feature Depth
        product_candidates = [u for u in discovered_urls if any(k in u.lower() for k in ["features", "product", "solutions", "case-studies"])]
        for u in product_candidates[:2]:
            if u.lower().rstrip("/") not in crawled_urls_set:
                targets.append(AcquisitionTarget(
                    target_type="page",
                    url_pattern=u,
                    rationale="Deepens product capability understanding and topical authority.",
                    expected_uncertainty_reduction=0.20,
                    priority=3
                ))

        return targets
