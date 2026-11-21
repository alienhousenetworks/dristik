"""Department A — Business and Conversion Strategy Specialists.

Covers: Business Model, Conversion Goals, Audience Intelligence, Customer Intent,
Offer Intelligence, Conversion Strategy, and Journey Mapping.
"""
from __future__ import annotations

from typing import List

from app.cro.models import (
    CROAgentOutput,
    CROBusinessModelType,
    CRODimensionCheck,
    CROFinding,
    CROSeverity,
    EvidenceSourceType,
)
from app.cro.specialists import CROAuditContext


def run_department_a(ctx: CROAuditContext) -> CROAgentOutput:
    findings: List[CROFinding] = []
    evidence_ids: List[str] = [ctx.profile.profile_id]
    limitations: List[str] = []

    primary_goals = [g for g in ctx.goals if g.goal_type == "primary"]
    has_primary_goal = bool(primary_goals and ctx.profile.primary_conversion != "unknown")
    model_known = ctx.profile.business_type != CROBusinessModelType.UNKNOWN

    # Check 1: Business model & goal clarity
    ctx.dimension_checks.append(
        CRODimensionCheck(
            check_id="dept_a_goal_alignment",
            dimension_id="conversion_journey",
            label="Business model and primary conversion goal identified",
            weight=1.0,
            result=1.0 if (model_known and has_primary_goal) else 0.5,
            source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
            evidence_ids=[ctx.profile.profile_id],
            note=ctx.profile.inference_basis,
        )
    )

    if not model_known:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-STRAT-{ctx.audit_id[-6:]}-01",
                category="conversion_strategy",
                subcategory="business_model",
                department="A",
                agent_id="cro_business_model",
                title="Primary Business Model & Conversion Goal Not Explicitly Clear",
                description="Crawled pages did not present clear commercial conversion signals to unambiguously determine the business model or primary conversion action.",
                root_cause="Missing explicit offer framing and conversion goal configuration.",
                affected_urls=[ctx.target_url],
                evidence_ids=[ctx.profile.profile_id],
                source_type=EvidenceSourceType.HEURISTIC_OBSERVATION,
                severity=CROSeverity.MEDIUM,
                confidence=0.75,
                recommendation="Configure the CRO business profile with explicit primary/secondary conversion goals and clarify the primary offer on entry pages.",
                implementation_instructions="Define primary conversion goal in Dristik CRO Business Profile and align entry-page hero copy and CTA to that exact action.",
                owner_role="Product / Marketing",
                effort="low",
                priority_score=65.0,
                acceptance_criteria=[
                    "Business model and primary conversion goal configured in CRO profile.",
                    "Homepage hero communicates the primary offer and target action.",
                ],
            )
        )

    # Check 2: Journey completeness & dead-ends / loops from Discovery
    dead_ends = ctx.journey_graph.get("dead_ends") or []
    loops = ctx.journey_graph.get("navigation_loops") or []
    broken_journeys = ctx.journey_graph.get("broken_journeys") or []

    journey_score = 1.0
    if broken_journeys:
        journey_score -= 0.4
    if dead_ends:
        journey_score -= 0.35
    if loops:
        journey_score -= 0.2
    journey_score = max(0.0, round(journey_score, 2))

    ctx.dimension_checks.append(
        CRODimensionCheck(
            check_id="dept_a_journey_integrity",
            dimension_id="conversion_journey",
            label="Conversion journey progression without dead ends or broken paths",
            weight=2.0,
            result=journey_score,
            source_type=EvidenceSourceType.DIRECT_TECHNICAL,
            evidence_ids=[j.journey_id for j in ctx.journeys],
            note=f"{len(dead_ends)} dead end(s), {len(loops)} loop(s), {len(broken_journeys)} broken link(s).",
        )
    )

    if dead_ends:
        findings.append(
            CROFinding(
                tenant_id=ctx.tenant_id,
                audit_id=ctx.audit_id,
                finding_id=f"CRO-JRN-{ctx.audit_id[-6:]}-01",
                category="funnel_optimization",
                subcategory="journey_dead_end",
                department="A",
                agent_id="cro_journey_mapping",
                title=f"Conversion Journey Dead Ends Detected on {len(dead_ends)} Page(s)",
                description=f"Crawled page(s) ({', '.join(dead_ends[:5])}) have no outbound conversion CTAs or onward navigation pathways.",
                root_cause="Terminal page template omits primary conversion CTA and onward navigation links.",
                affected_urls=list(dead_ends[:10]),
                affected_journeys=[j.journey_id for j in ctx.journeys],
                evidence_ids=[j.journey_id for j in ctx.journeys],
                source_type=EvidenceSourceType.DIRECT_TECHNICAL,
                severity=CROSeverity.HIGH,
                confidence=0.92,
                recommendation="Add a contextually matched primary conversion CTA and secondary exploration links to every terminal page template.",
                implementation_instructions="Update page template footer/content end block to render the primary goal CTA and related product/service links.",
                owner_role="Design / Engineering",
                effort="low",
                priority_score=80.0,
                acceptance_criteria=[
                    "Zero dead-end pages among audited commercial/entry URLs.",
                    "Each page links cleanly to the next conversion journey step.",
                ],
            )
        )

    if ctx.profile.unknown_fields:
        limitations.append(
            f"Partial business configuration; unknown fields preserved as unknown: {', '.join(ctx.profile.unknown_fields[:8])}."
        )

    ctx.artifacts["strategy_summary"] = {
        "business_model": ctx.profile.business_type.value,
        "primary_conversion": ctx.profile.primary_conversion,
        "secondary_conversions": ctx.profile.secondary_conversions,
        "goals_registered": len(ctx.goals),
        "audiences_registered": len(ctx.audiences),
        "journeys_mapped": len(ctx.journeys),
        "dead_ends_count": len(dead_ends),
        "navigation_loops_count": len(loops),
        "roles_executed": [
            "cro_business_model",
            "cro_conversion_goal",
            "cro_audience_intelligence",
            "cro_customer_intent",
            "cro_offer_intelligence",
            "cro_conversion_strategy",
            "cro_journey_mapping",
        ],
    }

    return CROAgentOutput(
        agent_id="cro_department_a_strategy",
        department="A",
        status="completed",
        audit_id=ctx.audit_id,
        findings=findings,
        evidence_ids=evidence_ids + [j.journey_id for j in ctx.journeys],
        confidence=ctx.profile.confidence or 0.75,
        limitations=limitations,
        artifacts=ctx.artifacts["strategy_summary"],
    )
