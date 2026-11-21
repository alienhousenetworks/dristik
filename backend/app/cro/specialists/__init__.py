"""CRO Specialist Agent Workforce Registry (Departments A–J).

Every specialist returns a validated CROAgentOutput contract (`agent_id`, `department`,
`status`, `audit_id`, `findings`, `evidence_ids`, `confidence`, `limitations`,
`methodology_version`, `execution_metadata`, `artifacts`).

Validation guardrails:
- Rejects fabricated conversion uplift claims or ungrounded revenue numbers.
- Stamps every finding with its exact EvidenceSourceType and claim boundary.
- Deterministic browser/DOM/analytics checks execute first; optional LLM copy
  enrichment is strictly bounded to factual page inputs.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from app.cro.models import (
    CRO_METHODOLOGY_VERSION,
    CROAgentOutput,
    CROAudience,
    CROBusinessProfile,
    CRODimensionCheck,
    CROFinding,
    CROGoal,
    CROInteractionTest,
    CROJourney,
    CROPage,
    CROPageElement,
    EVIDENCE_CLAIM_BOUNDARIES,
    EvidenceSourceType,
)

# Phrases that indicate fabricated uplift / revenue guarantees when not backed by an experiment
_FORBIDDEN_UNVERIFIED_CLAIM_RE = re.compile(
    r"(guaranteed\s+\d+%\s+(?:uplift|increase|lift)|will\s+increase\s+conversions?\s+by\s+\d+%|"
    r"boost(?:ing)?\s+conversion\s+by\s+up\s+to\s+\d+%|losing\s+\$[\d,]+\s+per\s+month)",
    re.I,
)


@dataclass
class CROAuditContext:
    """Shared execution context passed through the CRO DAG and all 10 departments."""

    tenant_id: str
    audit_id: str
    domain: str
    target_url: str
    profile: CROBusinessProfile
    goals: List[CROGoal] = field(default_factory=list)
    audiences: List[CROAudience] = field(default_factory=list)
    scope: Dict[str, Any] = field(default_factory=dict)
    pages: List[CROPage] = field(default_factory=list)
    raw_html_map: Dict[str, str] = field(default_factory=dict)
    journeys: List[CROJourney] = field(default_factory=list)
    journey_graph: Dict[str, Any] = field(default_factory=dict)
    elements: List[CROPageElement] = field(default_factory=list)
    interaction_tests: List[CROInteractionTest] = field(default_factory=list)
    analytics_payload: Optional[Dict[str, Any]] = None
    campaign_context: Optional[Dict[str, Any]] = None
    crm_payload: Optional[Dict[str, Any]] = None
    commerce_payload: Optional[Dict[str, Any]] = None
    field_cwv_payload: Optional[Dict[str, Any]] = None
    connected_providers: List[str] = field(default_factory=list)
    dimension_checks: List[CRODimensionCheck] = field(default_factory=list)
    all_findings: List[CROFinding] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)


DEPARTMENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "A": {
        "name": "Business and Conversion Strategy",
        "roles": [
            "cro_business_model",
            "cro_conversion_goal",
            "cro_audience_intelligence",
            "cro_customer_intent",
            "cro_offer_intelligence",
            "cro_conversion_strategy",
            "cro_journey_mapping",
        ],
    },
    "B": {
        "name": "UX and Usability",
        "roles": [
            "cro_navigation",
            "cro_information_architecture",
            "cro_usability",
            "cro_interaction",
            "cro_readability",
            "cro_cognitive_load",
            "cro_journey_friction",
            "cro_mobile_usability",
            "cro_accessibility",
        ],
    },
    "C": {
        "name": "UI and Visual Hierarchy",
        "roles": [
            "cro_visual_hierarchy",
            "cro_layout",
            "cro_cta_visibility",
            "cro_typography",
            "cro_color_contrast",
            "cro_responsive_design",
            "cro_design_consistency",
        ],
    },
    "D": {
        "name": "Landing Pages and Copywriting",
        "roles": [
            "cro_landing_page",
            "cro_message_match",
            "cro_headline",
            "cro_value_proposition",
            "cro_benefit_clarity",
            "cro_objection_handling",
            "cro_copywriting",
            "cro_cta_copy",
            "cro_trust_copy",
        ],
    },
    "E": {
        "name": "Forms and Lead Generation",
        "roles": [
            "cro_form_discovery",
            "cro_form_usability",
            "cro_field_necessity",
            "cro_form_validation",
            "cro_error_messaging",
            "cro_lead_qualification",
            "cro_contact_journey",
        ],
    },
    "F": {
        "name": "Ecommerce and Checkout",
        "roles": [
            "cro_product_page",
            "cro_product_information",
            "cro_pricing",
            "cro_cart",
            "cro_checkout",
            "cro_payment",
            "cro_shipping_returns",
            "cro_subscription",
            "cro_ecommerce_funnel",
        ],
    },
    "G": {
        "name": "Trust and Persuasion",
        "roles": [
            "cro_trust_signal",
            "cro_review_testimonial",
            "cro_credibility",
            "cro_security_reassurance",
            "cro_policy_transparency",
            "cro_risk_reversal",
            "cro_brand_consistency",
        ],
    },
    "H": {
        "name": "Performance and Technical Experience",
        "roles": [
            "cro_performance",
            "cro_core_web_vitals",
            "cro_js_interaction",
            "cro_rendering",
            "cro_error_detection",
            "cro_device_compatibility",
            "cro_third_party_scripts",
        ],
    },
    "I": {
        "name": "Analytics and Conversion Intelligence",
        "roles": [
            "cro_analytics_config",
            "cro_event_tracking",
            "cro_funnel",
            "cro_dropoff",
            "cro_attribution",
            "cro_segment",
            "cro_revenue_intelligence",
            "cro_data_quality",
        ],
    },
    "J": {
        "name": "Experimentation and Optimization",
        "roles": [
            "cro_finding_validation",
            "cro_root_cause",
            "cro_opportunity",
            "cro_prioritization",
            "cro_hypothesis",
            "cro_experiment_design",
            "cro_remediation",
            "cro_verification",
            "cro_regression",
            "cro_report_qa",
        ],
    },
}


def validate_agent_output(output: CROAgentOutput) -> CROAgentOutput:
    """Enforce epistemic boundaries and structural integrity on every specialist output."""
    clean_findings: List[CROFinding] = []
    for f in output.findings:
        if not f.claim_boundary:
            f.claim_boundary = EVIDENCE_CLAIM_BOUNDARIES.get(f.source_type.value, "Observation")
        # Strip/reject unverified conversion uplift or fabricated revenue guarantees
        if f.source_type != EvidenceSourceType.EXPERIMENT_RESULT:
            for field_name in ("description", "business_impact", "recommendation"):
                val = getattr(f, field_name, None)
                if isinstance(val, str) and _FORBIDDEN_UNVERIFIED_CLAIM_RE.search(val):
                    setattr(
                        f,
                        field_name,
                        _FORBIDDEN_UNVERIFIED_CLAIM_RE.sub(
                            "[unverified uplift statement removed; validate via controlled experiment]",
                            val,
                        ),
                    )
        # Ensure non-hypothesis findings carry traceable evidence or downgrade transparently
        if not f.evidence_ids and f.source_type not in (
            EvidenceSourceType.HEURISTIC_OBSERVATION,
            EvidenceSourceType.AI_HYPOTHESIS,
        ):
            f.source_type = EvidenceSourceType.HEURISTIC_OBSERVATION
            f.claim_boundary = EVIDENCE_CLAIM_BOUNDARIES[EvidenceSourceType.HEURISTIC_OBSERVATION.value]
            f.limitations.append("Downgraded to heuristic_observation because no direct evidence ID was attached.")
        clean_findings.append(f)

    output.findings = clean_findings
    output.methodology_version = CRO_METHODOLOGY_VERSION
    return output


def run_all_departments(ctx: CROAuditContext) -> List[CROAgentOutput]:
    """Execute Departments A through I in deterministic order and validate every output."""
    from app.cro.specialists.strategy import run_department_a
    from app.cro.specialists.ux_ui import run_department_b, run_department_c
    from app.cro.specialists.landing_copy import run_department_d
    from app.cro.specialists.forms_cta import run_department_e
    from app.cro.specialists.ecommerce_trust import run_department_f, run_department_g
    from app.cro.specialists.performance_tech import run_department_h
    from app.cro.specialists.analytics_attribution import run_department_i

    runners: Sequence[Callable[[CROAuditContext], CROAgentOutput]] = (
        run_department_a,
        run_department_b,
        run_department_c,
        run_department_d,
        run_department_e,
        run_department_f,
        run_department_g,
        run_department_h,
        run_department_i,
    )
    outputs: List[CROAgentOutput] = []
    for fn in runners:
        started = time.monotonic()
        out = fn(ctx)
        out.execution_metadata["elapsed_ms"] = round((time.monotonic() - started) * 1000.0, 2)
        validated = validate_agent_output(out)
        outputs.append(validated)
        ctx.all_findings.extend(validated.findings)
    return outputs
