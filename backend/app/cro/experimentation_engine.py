"""
Statistical CRO Experimentation Recommendation Engine (Phase 6.9).

Generates rigorously structured A/B and multivariate experiment plans:
- Hypothesis ("If [variation], then [primary metric lift], because [behavioral mechanism]")
- Target audience & device segmentation
- Page or flow URL
- Proposed variation specifications (DOM edits, copy rewrites)
- Expected behavioral mechanism
- Primary metric & Guardrail metrics
- Experiment design (A/B Test, Multivariate, Split URL)
- Sample-size requirements (Evan Miller two-tailed power calculation)
- Duration considerations (minimum 14 days / 2 business cycles)
- Result and statistical confidence rules

Notice: Only call an improvement successful after actual experiment data supports it.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.models import Finding


class ExperimentSpec(BaseModel):
    experiment_id: str
    title: str
    hypothesis: str
    target_audience: str = "All traffic (Desktop + Mobile)"
    page_or_flow: str
    proposed_variation: str
    expected_mechanism: str
    primary_metric: str
    guardrail_metrics: List[str] = Field(default_factory=lambda: ["Bounce Rate", "Downstream Form Completion", "Refunds"])
    experiment_design: str = "A/B Two-Tailed Randomized Split"
    baseline_conversion_rate_est: float = 0.025 # 2.5% default baseline
    minimum_detectable_effect_pct: float = 15.0 # 15% relative lift
    sample_size_per_variant: int = 12500
    total_required_sample_size: int = 25000
    minimum_duration_days: int = 14 # 2 full weekly business cycles
    status: str = "PROPOSED_AWAITING_EXECUTION"
    success_criteria: str = "p-value < 0.05 (95% statistical confidence) and guardrails unviolated."


class ExperimentationEngine:
    """Calculates power requirements and synthesizes testable experiment proposals."""

    @classmethod
    def calculate_sample_size(
        cls,
        baseline_cr: float = 0.025,
        relative_mde: float = 0.15,
        alpha: float = 0.05,
        power: float = 0.80,
    ) -> int:
        """
        Two-tailed sample size per variant for proportions (standard normal approximation).
        Z_alpha/2 = 1.96 for alpha=0.05
        Z_beta = 0.8416 for power=0.80
        """
        if baseline_cr <= 0 or baseline_cr >= 1.0 or relative_mde <= 0:
            return 10000

        p1 = baseline_cr
        p2 = p1 * (1.0 + relative_mde)
        p_avg = (p1 + p2) / 2.0

        z_alpha = 1.95996
        z_beta = 0.84162

        numerator = (z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p2 - p1) ** 2

        if denominator == 0:
            return 10000
        n_per_variant = math.ceil(numerator / denominator)
        return max(1000, n_per_variant)

    @classmethod
    def generate_experiments(
        cls,
        findings: List[Finding],
        value_prop_defects: Optional[List[Dict[str, Any]]] = None,
        journey_defects: Optional[List[Dict[str, Any]]] = None,
        cta_passive_items: Optional[List[Any]] = None,
        domain: str = "",
    ) -> List[ExperimentSpec]:
        experiments: List[ExperimentSpec] = []
        exp_idx = 1

        # 1. Experiment on Hero Value Proposition / Headline
        experiments.append(ExperimentSpec(
            experiment_id=f"EXP-{domain.replace('.', '-').upper()[:6] or 'CRO'}-{exp_idx:02d}",
            title="Outcome-Focused Hero Value Proposition vs Feature Headline",
            hypothesis="If we replace abstract corporate slogans with an outcome-oriented headline stating the specific benefit and target audience, then visitor-to-CTA click-through rate will increase by 15%, because prospective buyers immediately comprehend the core offering.",
            page_or_flow="Homepage / Primary Landing Page",
            proposed_variation="Hero H1: 'Scale Enterprise Revenue with Automated Intelligence' + 3 supporting proof bullet points.",
            expected_mechanism="Reduces cognitive load and satisfies the first 3 buyer questions in the initial viewport.",
            primary_metric="Primary CTA Click-Through Rate (CTR)",
            guardrail_metrics=["Bounce Rate", "Session Duration", "Downstream Dropoff"],
            experiment_design="A/B Two-Tailed Split (50/50)",
            baseline_conversion_rate_est=0.03,
            minimum_detectable_effect_pct=15.0,
            sample_size_per_variant=cls.calculate_sample_size(0.03, 0.15),
            total_required_sample_size=cls.calculate_sample_size(0.03, 0.15) * 2,
            minimum_duration_days=14,
        ))
        exp_idx += 1

        # 2. Experiment on CTA wording & Prominence
        experiments.append(ExperimentSpec(
            experiment_id=f"EXP-{domain.replace('.', '-').upper()[:6] or 'CRO'}-{exp_idx:02d}",
            title="Value-Driven Action CTA vs Passive 'Learn More' Button",
            hypothesis="If we replace passive 'Learn more' and 'Submit' buttons with action-oriented microcopy ('Get Your Free Audit' / 'Start Free Trial'), then click conversion will rise by 20%, because active verbs create higher perceived momentum.",
            page_or_flow="All High-Traffic Landing Pages",
            proposed_variation="Button text: 'Start Your Free 14-Day Trial' with subtle directional arrow and reassurance microcopy ('No credit card required').",
            expected_mechanism="High-intent copy eliminates passive friction and clarifies immediate value.",
            primary_metric="Form Initiation Rate",
            guardrail_metrics=["Form Completion Rate", "Lead Quality Score"],
            experiment_design="A/B Split (50/50)",
            baseline_conversion_rate_est=0.02,
            minimum_detectable_effect_pct=20.0,
            sample_size_per_variant=cls.calculate_sample_size(0.02, 0.20),
            total_required_sample_size=cls.calculate_sample_size(0.02, 0.20) * 2,
            minimum_duration_days=14,
        ))
        exp_idx += 1

        # 3. Experiment on Form Field Reduction / Multi-Step
        experiments.append(ExperimentSpec(
            experiment_id=f"EXP-{domain.replace('.', '-').upper()[:6] or 'CRO'}-{exp_idx:02d}",
            title="Progressive 2-Step Lead Capture vs Monolithic Form",
            hypothesis="If we split the monolithic 7-field lead capture form into a 2-step progressive flow (Step 1: Work Email; Step 2: Name & Company Size), then overall form completion will lift by 18%, because psychological commitment bias reduces form abandonment.",
            page_or_flow="Lead Form / Contact Route",
            proposed_variation="Step 1 presents a single email input with 'Continue ->'; Step 2 displays pre-filled email and remaining qualifying inputs.",
            expected_mechanism="Lowers initial friction barrier and leverages the Foot-in-the-Door persuasion principle.",
            primary_metric="Form Completion / Submission Rate",
            guardrail_metrics=["Qualified Lead Rate", "Email Verification Failure Rate"],
            experiment_design="A/B Split Test",
            baseline_conversion_rate_est=0.05,
            minimum_detectable_effect_pct=18.0,
            sample_size_per_variant=cls.calculate_sample_size(0.05, 0.18),
            total_required_sample_size=cls.calculate_sample_size(0.05, 0.18) * 2,
            minimum_duration_days=14,
        ))

        return experiments


experimentation_engine = ExperimentationEngine()
