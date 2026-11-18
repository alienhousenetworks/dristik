"""
Actionable CRO Recommendations Suite across 10 Priority Areas (Phase 6.11).

Generates concrete remediation actions across:
1. Hero section improvements
2. CTA hierarchy recommendations
3. Navigation restructuring
4. Form simplification
5. Trust signal placement
6. Pricing clarity improvements
7. Product information improvements
8. Checkout friction reduction
9. Mobile layout changes
10. Prioritized experiment proposals
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.models import Finding
from app.cro.experimentation_engine import ExperimentSpec


class CroRecommendationCategory(BaseModel):
    category_id: str
    title: str
    priority: int # 1 = highest
    actionable_remedies: List[str] = Field(default_factory=list)
    impact_level: str = "HIGH" # HIGH | MEDIUM | LOW
    effort_level: str = "LOW" # LOW | MEDIUM | HIGH


class CroComprehensiveRecommendations(BaseModel):
    categories: List[CroRecommendationCategory] = Field(default_factory=list)
    total_actions_count: int = 0
    top_3_quick_wins: List[str] = Field(default_factory=list)


class RecommendationGenerator:
    """Compiles recommendations across the 10 core CRO dimensions."""

    @classmethod
    def generate(
        cls,
        hero_headline: str = "",
        passive_ctas_count: int = 0,
        journey_loops_count: int = 0,
        dead_ends_count: int = 0,
        form_missing_labels: int = 0,
        form_high_friction_count: int = 0,
        mobile_defects_count: int = 0,
        experiments: Optional[List[ExperimentSpec]] = None,
        pricing_detected: bool = False,
    ) -> CroComprehensiveRecommendations:
        cats: List[CroRecommendationCategory] = []

        # 1. Hero Section Improvements
        cats.append(CroRecommendationCategory(
            category_id="hero_improvements",
            title="Hero Section & 5-Second Comprehension",
            priority=1,
            actionable_remedies=[
                f"Rewrite hero headline ('{hero_headline[:45]}...') to explicitly articulate the primary product category and specific outcome.",
                "Position 3 concrete proof bullet points (e.g. key metric lift, enterprise certification) immediately beneath the primary subhead.",
                "Ensure hero heading and primary CTA are co-located in the initial 600px of vertical viewport height.",
            ],
            impact_level="HIGH",
            effort_level="LOW",
        ))

        # 2. CTA Hierarchy Recommendations
        cta_remedies = [
            "Establish a clear visual hierarchy: 1 primary high-contrast action button paired with a secondary text or ghost button.",
        ]
        if passive_ctas_count > 0:
            cta_remedies.append(f"Upgrade {passive_ctas_count} passive buttons ('Learn more', 'Submit') to value-rich action verbs ('Claim Your Audit', 'Start Free Trial').")
        cta_remedies.append("Ensure primary action contrast ratio exceeds 4.5:1 against the surrounding container background.")
        cats.append(CroRecommendationCategory(
            category_id="cta_hierarchy",
            title="CTA Hierarchy & Microcopy",
            priority=1,
            actionable_remedies=cta_remedies,
            impact_level="HIGH",
            effort_level="LOW",
        ))

        # 3. Navigation Restructuring
        nav_remedies = [
            "Limit primary navigation items to 5–7 high-level categories to prevent choice paralysis.",
        ]
        if journey_loops_count > 0:
            nav_remedies.append(f"Break {journey_loops_count} detected circular navigation loops with progressive breadcrumbs.")
        if dead_ends_count > 0:
            nav_remedies.append(f"Introduce contextual onward conversion triggers on {dead_ends_count} dead-end terminal pages.")
        cats.append(CroRecommendationCategory(
            category_id="navigation_restructure",
            title="Navigation Architecture & Journey Continuity",
            priority=2,
            actionable_remedies=nav_remedies,
            impact_level="MEDIUM",
            effort_level="MEDIUM",
        ))

        # 4. Form Simplification
        form_remedies = []
        if form_missing_labels > 0:
            form_remedies.append(f"Associate explicit <label for='...'> tags on {form_missing_labels} input elements to satisfy accessibility and avoid disappearing labels.")
        if form_high_friction_count > 0:
            form_remedies.append("Deconstruct long forms into a 2-step progressive disclosure flow to minimize perceived cognitive effort.")
        form_remedies.extend([
            "Enable browser autofill via standard autocomplete attributes (`name`, `email`, `tel`, `address-line1`).",
            "Set appropriate mobile keyboard triggers (`type='tel'`, `type='email'`, `inputmode='numeric'`).",
        ])
        cats.append(CroRecommendationCategory(
            category_id="form_simplification",
            title="Form Ergonomics & Lead Capture Simplification",
            priority=1,
            actionable_remedies=form_remedies,
            impact_level="HIGH",
            effort_level="LOW",
        ))

        # 5. Trust Signal Placement
        cats.append(CroRecommendationCategory(
            category_id="trust_placement",
            title="Trust Signal & Credibility Placement",
            priority=2,
            actionable_remedies=[
                "Place recognizable customer logos and trust badges (SOC 2, ISO, PCI-DSS) immediately adjacent to lead forms and checkout buttons.",
                "Include verifiable customer quotes featuring full names, job titles, and quantified business impact.",
                "Add clear reassurance microcopy near credit card fields ('256-bit SSL encrypted • Cancel anytime').",
            ],
            impact_level="HIGH",
            effort_level="LOW",
        ))

        # 6. Pricing Clarity Improvements
        pricing_remedies = [
            "Display transparent pricing tiers with default annual/monthly toggle showing percentage discount savings.",
            "Highlight the 'Most Popular' or 'Recommended' tier with visual distinction and contrasting badge.",
            "Provide an explicit comparison table detailing included features across tiers.",
        ]
        if not pricing_detected:
            pricing_remedies.insert(0, "Provide a dedicated '/pricing' link in the primary header navigation.")
        cats.append(CroRecommendationCategory(
            category_id="pricing_clarity",
            title="Pricing Transparency & Packaging Psychology",
            priority=2,
            actionable_remedies=pricing_remedies,
            impact_level="HIGH",
            effort_level="MEDIUM",
        ))

        # 7. Product Information Improvements
        cats.append(CroRecommendationCategory(
            category_id="product_information",
            title="Product Information & Specification Completeness",
            priority=3,
            actionable_remedies=[
                "Provide high-resolution imagery showcasing the product in real-world context with interactive zoom.",
                "Structure technical specifications into scannable accordion tabs (Dimensions, Compatibility, Materials).",
                "Display authentic customer reviews with search, filter, and rating distributions.",
            ],
            impact_level="MEDIUM",
            effort_level="MEDIUM",
        ))

        # 8. Checkout Friction Reduction
        cats.append(CroRecommendationCategory(
            category_id="checkout_friction",
            title="Checkout & Transaction Friction Reduction",
            priority=1,
            actionable_remedies=[
                "Support frictionless 1-click Express Checkout (Apple Pay, Google Pay, PayPal).",
                "Ensure guest checkout is prominently available without forcing upfront account creation.",
                "Collapse discount/coupon code fields into a subtle text link to prevent visitors from leaving the cart to hunt for coupons.",
            ],
            impact_level="HIGH",
            effort_level="MEDIUM",
        ))

        # 9. Mobile Layout Changes
        mobile_remedies = [
            "Implement a sticky bottom conversion bar on mobile viewports so primary action remains accessible during scroll.",
            "Ensure all interactive tap targets satisfy WCAG 2.2 SC 2.5.8 minimum 24×24px (recommended 44×44px).",
            "Eliminate horizontal scrolling by enforcing responsive fluid containers across 360px and 390px widths.",
        ]
        cats.append(CroRecommendationCategory(
            category_id="mobile_layout",
            title="Mobile Responsive & Touch Ergonomics",
            priority=1,
            actionable_remedies=mobile_remedies,
            impact_level="HIGH",
            effort_level="LOW",
        ))

        # 10. Prioritized Experiment Proposals
        exp_remedies = []
        for exp in (experiments or [])[:3]:
            exp_remedies.append(f"Execute {exp.experiment_id}: '{exp.title}' targeting {exp.target_audience} for a minimum of {exp.minimum_duration_days} days.")
        cats.append(CroRecommendationCategory(
            category_id="experiment_proposals",
            title="Scientific Experimentation Proposals",
            priority=1,
            actionable_remedies=exp_remedies or ["Launch A/B tests targeting hero value proposition clarity and CTA action microcopy."],
            impact_level="HIGH",
            effort_level="MEDIUM",
        ))

        # Top 3 Quick Wins
        quick_wins = [
            "Upgrade passive button microcopy ('Submit', 'Learn More') to benefit-driven CTAs.",
            "Deploy sticky mobile conversion button and add explicit input labels on all lead forms.",
            "Add reassurance trust microcopy ('No credit card required' / 'Cancel anytime') adjacent to primary hero button.",
        ]

        total_actions = sum(len(c.actionable_remedies) for c in cats)

        return CroComprehensiveRecommendations(
            categories=cats,
            total_actions_count=total_actions,
            top_3_quick_wins=quick_wins,
        )


recommendation_generator = RecommendationGenerator()
