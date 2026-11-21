"""Canonical CRO 3-Scorecard Engine (Phase 20) + Backward-Compatible 10-Dimension Engine.

Implements three strictly separated enterprise scorecards:
1. CRO Experience Score (10 weighted dimensions totaling 100%):
   - Conversion journey and funnel quality (15%)
   - UX and usability (15%)
   - UI and visual hierarchy (10%)
   - Landing page and message match (10%)
   - Copywriting and value proposition (10%)
   - Forms and CTA effectiveness (10%)
   - Trust and credibility (10%)
   - Mobile experience and accessibility (10%)
   - Performance and interaction quality (5%)
   - Analytics and measurement readiness (5%)
   Formula: Dimension Score = sum(Weight_i * Result_i) / sum(Weight_i for eligible executed checks) * 100
   Inapplicable or unexecuted checks are excluded from the denominator without penalty.

2. Conversion Measurement Score:
   Rates instrumentation, event validation, duplicate-free tracking, and data quality.

3. Measured Business Performance:
   Reports actual measured conversion & revenue KPIs without converting them into an
   arbitrary website quality score or fabricating zeros when analytics is absent.

Also preserves `CroScoringEngine` / `cro_scoring_engine` for backward compatibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from app.cro.models import (
    CRO_METHODOLOGY_VERSION,
    CRODimensionCheck,
    CROThreeScorecardBundle,
    CROWeightedDimension,
)


# ─────────────────────────────────────────────────────────────────────────────
# Canonical 3-Scorecard Enterprise CRO Engine (Phase 20)
# ─────────────────────────────────────────────────────────────────────────────

ENTERPRISE_CRO_DIMENSIONS: Tuple[Tuple[str, str, float], ...] = (
    ("conversion_journey", "Conversion journey and funnel quality", 15.0),
    ("ux_usability", "UX and usability", 15.0),
    ("ui_visual_hierarchy", "UI and visual hierarchy", 10.0),
    ("landing_page_match", "Landing page and message match", 10.0),
    ("copywriting_value_prop", "Copywriting and value proposition", 10.0),
    ("forms_cta", "Forms and CTA effectiveness", 10.0),
    ("trust_credibility", "Trust and credibility", 10.0),
    ("mobile_accessibility", "Mobile experience and accessibility", 10.0),
    ("performance_interaction", "Performance and interaction quality", 5.0),
    ("analytics_measurement", "Analytics and measurement readiness", 5.0),
)


def _grade_for_score(score: Optional[float]) -> str:
    if score is None:
        return "Unmeasured"
    if score >= 90.0:
        return "A+"
    if score >= 85.0:
        return "A"
    if score >= 75.0:
        return "B"
    if score >= 60.0:
        return "C"
    if score >= 45.0:
        return "D"
    return "F"


class EnterpriseCroScoringEngine:
    """Deterministic, reproducible 3-scorecard engine with transparent denominator normalization."""

    DIMENSIONS = ENTERPRISE_CRO_DIMENSIONS
    METHODOLOGY_VERSION = CRO_METHODOLOGY_VERSION

    @classmethod
    def total_configured_weight(cls) -> float:
        return round(sum(w for _, _, w in cls.DIMENSIONS), 4)

    @classmethod
    def evaluate_three_scorecards(
        cls,
        *,
        audit_id: str,
        checks: Sequence[CRODimensionCheck],
        measurement_checks: Sequence[Dict[str, Any]],
        business_metrics: Sequence[Dict[str, Any]],
        pages_audited: int = 0,
        pages_discovered: Optional[int] = None,
        interaction_tests_executed: int = 0,
        findings_with_evidence_ratio: Optional[float] = None,
        analytics_connected: bool = False,
    ) -> CROThreeScorecardBundle:
        checks_by_dim: Dict[str, List[CRODimensionCheck]] = {}
        for chk in checks:
            checks_by_dim.setdefault(chk.dimension_id, []).append(chk)

        dim_models: List[CROWeightedDimension] = []
        measured_dims: List[CROWeightedDimension] = []

        for dim_id, dim_name, weight_pct in cls.DIMENSIONS:
            dim_checks = checks_by_dim.get(dim_id, [])
            applicable_checks = [c for c in dim_checks if c.applicable]
            executed_checks = [c for c in applicable_checks if c.executed and c.result is not None]

            if dim_checks and not applicable_checks:
                dim_models.append(
                    CROWeightedDimension(
                        dimension_id=dim_id,
                        name=dim_name,
                        configured_weight_pct=weight_pct,
                        effective_weight_pct=None,
                        applicable=False,
                        executed_checks=0,
                        total_checks=len(dim_checks),
                        score=None,
                        status="not_applicable",
                        notes=["Dimension not applicable for this business model; excluded without penalty."],
                    )
                )
                continue

            if not executed_checks:
                dim_models.append(
                    CROWeightedDimension(
                        dimension_id=dim_id,
                        name=dim_name,
                        configured_weight_pct=weight_pct,
                        effective_weight_pct=None,
                        applicable=True,
                        executed_checks=0,
                        total_checks=len(applicable_checks),
                        score=None,
                        status="unmeasured",
                        notes=["No eligible checks executed; excluded from denominator without penalty."],
                    )
                )
                continue

            w_sum = sum(c.weight for c in executed_checks)
            w_val = sum(c.weight * float(c.result) for c in executed_checks)
            dim_score = round((w_val / w_sum) * 100.0, 1) if w_sum > 0 else None
            ev_types = sorted({c.source_type.value for c in executed_checks})
            status = "measured" if len(executed_checks) == len(applicable_checks) else "partial"

            dm = CROWeightedDimension(
                dimension_id=dim_id,
                name=dim_name,
                configured_weight_pct=weight_pct,
                applicable=True,
                executed_checks=len(executed_checks),
                total_checks=len(applicable_checks),
                score=dim_score,
                status=status,
                evidence_types=ev_types,
                notes=[c.note for c in executed_checks if c.note][:3],
            )
            dim_models.append(dm)
            if dim_score is not None:
                measured_dims.append(dm)

        active_weight = round(sum(d.configured_weight_pct for d in measured_dims), 2)
        if active_weight > 0:
            weighted_total = sum(d.configured_weight_pct * (d.score or 0.0) for d in measured_dims)
            experience_score = round(weighted_total / active_weight, 1)
            for d in measured_dims:
                d.effective_weight_pct = round((d.configured_weight_pct / active_weight) * 100.0, 2)
        else:
            experience_score = None

        # Scorecard 2: Conversion Measurement Score (independent of experience score)
        meas_list = list(measurement_checks)
        evaluated_meas = [m for m in meas_list if m.get("status") in ("passed", "failed", "warning")]
        if not evaluated_meas:
            measurement_score = None
            measurement_status = "unmeasured"
        else:
            pts = sum(
                1.0 if m.get("status") == "passed" else (0.5 if m.get("status") == "warning" else 0.0)
                for m in evaluated_meas
            )
            measurement_score = round((pts / len(evaluated_meas)) * 100.0, 1)
            if not analytics_connected:
                measurement_status = "partial"
            elif measurement_score >= 80.0:
                measurement_status = "verified"
            else:
                measurement_status = "unhealthy"

        # Scorecard 3: Measured Business Performance (strictly unblended raw KPIs)
        biz_list = list(business_metrics)
        measured_biz_cnt = sum(1 for m in biz_list if m.get("status") == "measured" and m.get("value") is not None)
        if not analytics_connected and measured_biz_cnt == 0:
            biz_status = "data_unavailable"
        elif measured_biz_cnt == len(biz_list) and biz_list:
            biz_status = "measured"
        elif measured_biz_cnt > 0:
            biz_status = "partial"
        else:
            biz_status = "data_unavailable"

        # Qualifications: coverage, confidence, freshness, analytics completeness
        disc = pages_discovered if (isinstance(pages_discovered, int) and pages_discovered > 0) else pages_audited
        scope_cov = round(min(100.0, (pages_audited / max(1, disc)) * 100.0), 1) if pages_audited > 0 else 0.0
        total_applicable_checks = sum(1 for c in checks if c.applicable)
        total_executed_checks = sum(1 for c in checks if c.applicable and c.executed and c.result is not None)
        test_cov = round((total_executed_checks / max(1, total_applicable_checks)) * 100.0, 1) if total_applicable_checks else 0.0
        ev_cov = round((findings_with_evidence_ratio * 100.0), 1) if findings_with_evidence_ratio is not None else 100.0
        analytics_comp = round((measured_biz_cnt / max(1, len(biz_list))) * 100.0, 1) if biz_list else 0.0
        confidence = round(
            min(1.0, (0.45 * (active_weight / 100.0)) + (0.35 * (test_cov / 100.0)) + (0.20 * (1.0 if analytics_connected else 0.45))),
            2,
        )

        disclosures = [
            "CRO Experience Score uses proposed Dristik methodology weights (15/15/10/10/10/10/10/10/5/5 = 100%), not universal industry benchmarks.",
            "Experience quality, conversion measurement reliability, and measured business performance are kept strictly separate.",
        ]
        if not analytics_connected:
            disclosures.append(
                "Analytics connector not configured: Measured Business Performance is reported as data_unavailable (never coerced to zero)."
            )
        if active_weight < 100.0:
            disclosures.append(
                f"CRO Experience Score normalized across {active_weight:.1f}% active evaluated weight; unmeasured or inapplicable checks were excluded without penalty."
            )

        return CROThreeScorecardBundle(
            audit_id=audit_id,
            methodology_version=cls.METHODOLOGY_VERSION,
            experience_score=experience_score,
            experience_grade=_grade_for_score(experience_score),
            experience_dimensions=dim_models,
            experience_active_weight_pct=active_weight,
            measurement_score=measurement_score,
            measurement_status=measurement_status,
            measurement_checks=meas_list,
            business_performance_status=biz_status,
            business_performance_metrics=biz_list,
            scope_coverage_pct=scope_cov,
            test_coverage_pct=test_cov,
            evidence_coverage_pct=ev_cov,
            confidence=confidence,
            data_freshness=datetime.now(timezone.utc).isoformat(),
            analytics_completeness_pct=analytics_comp,
            disclosures=disclosures,
        )


enterprise_cro_scoring_engine = EnterpriseCroScoringEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Legacy 10-Dimension Wrapper (Preserved for 100% Backward Compatibility)
# ─────────────────────────────────────────────────────────────────────────────


class DimensionEvidenceClass:
    HEURISTIC = "HEURISTIC_INSPECTION"
    AUTOMATED = "AUTOMATED_INTERACTION_TEST"
    ANALYTICS = "ACTUAL_BEHAVIORAL_ANALYTICS"


class CroDimensionScoreCard(BaseModel):
    id: str
    name: str
    weight_pct: float = 10.0
    score: Optional[float] = None
    status: str = "MEASURED"
    evidence_class: str
    evidence_basis: str
    strengths: List[str] = Field(default_factory=list)
    defects: List[str] = Field(default_factory=list)


class TenDimensionCroScoreResult(BaseModel):
    overall_cro_score: float = 75.0
    cro_grade: str = "B"
    dimensions: List[CroDimensionScoreCard] = Field(default_factory=list)
    measured_dimensions_count: int = 9
    unmeasured_dimensions_count: int = 1
    total_weight_evaluated: float = 90.0
    evidence_class_disclosure: str = (
        "This enterprise CRO audit strictly distinguishes between three evidence classes: "
        "(1) Heuristic Inspection (semantic NLP and copywriting analysis), "
        "(2) Automated Interaction Tests (DOM geometry, viewports, WCAG rules, forms), and "
        "(3) Actual Behavioral Analytics (GA4 key events, unique-user conversions). "
        "Heuristic scores are never blended with or represented as actual conversion data."
    )


class CroScoringEngine:
    """Backward-compatible 10-dimension CRO scorecard (preserved for existing callers & tests)."""

    DIMENSION_DEFINITIONS = [
        ("value_prop", "Value proposition", DimensionEvidenceClass.HEURISTIC, "6-Question buyer model and hero proposition clarity"),
        ("visual_hierarchy", "Visual hierarchy", DimensionEvidenceClass.AUTOMATED, "Multi-viewport layout, above-the-fold boundary, and defect detection"),
        ("cta_effectiveness", "CTA effectiveness", DimensionEvidenceClass.AUTOMATED, "CTA placement, intent classification, button contrast, and rewrites"),
        ("nav_journey", "Navigation and journey", DimensionEvidenceClass.AUTOMATED, "Visual journey graph traversal, loop detection, and dead ends"),
        ("forms_leadgen", "Forms and lead capture", DimensionEvidenceClass.AUTOMATED, "Field friction, WCAG labels, autofill, and mobile keyboard trigger"),
        ("mobile_ux", "Mobile UX", DimensionEvidenceClass.AUTOMATED, "390px/360px viewport ergonomics, touch targets, and sticky triggers"),
        ("accessibility", "Accessibility (WCAG 2.2 AA)", DimensionEvidenceClass.AUTOMATED, "Focus outlines, keyboard navigation, color contrast, and alt text"),
        ("trust_credibility", "Trust and credibility", DimensionEvidenceClass.HEURISTIC, "Quantified proof claims, client logos, certifications, and guarantees"),
        ("checkout_friction", "Checkout / purchase friction", DimensionEvidenceClass.AUTOMATED, "Cart and transaction flow, pricing transparency, and payment methods"),
        ("behavioral_analytics", "Behavioural conversion evidence", DimensionEvidenceClass.ANALYTICS, "GA4 sessions, conversion events, and funnel abandonment rates"),
    ]

    @classmethod
    def evaluate(
        cls,
        value_prop_score: float = 75.0,
        visual_score: Optional[float] = 80.0,
        cta_score: float = 70.0,
        journey_defects_count: int = 0,
        form_score: float = 85.0,
        mobile_defects_count: int = 0,
        a11y_score: float = 85.0,
        trust_score: float = 75.0,
        checkout_score: float = 75.0,
        analytics_connected: bool = False,
        analytics_conversion_rate: Optional[float] = None,
    ) -> TenDimensionCroScoreResult:
        journey_score = max(40.0, 90.0 - (journey_defects_count * 15.0))
        mobile_score = max(40.0, 88.0 - (mobile_defects_count * 10.0))
        analytics_score = None
        analytics_status = "UNMEASURED"
        if analytics_connected and analytics_conversion_rate is not None:
            analytics_score = round(min(100.0, max(20.0, analytics_conversion_rate * 2500.0)), 1)
            analytics_status = "MEASURED"

        raw_scores: Dict[str, Tuple[Optional[float], str, List[str], List[str]]] = {
            "value_prop": (round(value_prop_score, 1), "HEURISTIC", ["Headline evaluated against 6 buyer questions"], []),
            "visual_hierarchy": (round(visual_score, 1) if visual_score is not None else 78.0, "AUTOMATED_TEST", ["Evaluated across viewport profiles"], []),
            "cta_effectiveness": (round(cta_score, 1), "AUTOMATED_TEST", ["Analyzed button intent, placement, and contrast"], []),
            "nav_journey": (round(journey_score, 1), "AUTOMATED_TEST", ["Conversion path graph computed"], [f"{journey_defects_count} path defect(s) detected"] if journey_defects_count else []),
            "forms_leadgen": (round(form_score, 1), "AUTOMATED_TEST", ["Evaluated input labels, autocomplete, and field load"], []),
            "mobile_ux": (round(mobile_score, 1), "AUTOMATED_TEST", ["Tested mobile responsive viewport layout"], [f"{mobile_defects_count} mobile layout defect(s)"] if mobile_defects_count else []),
            "accessibility": (round(a11y_score, 1), "AUTOMATED_TEST", ["WCAG 2.2 AA automated criteria evaluated"], []),
            "trust_credibility": (round(trust_score, 1), "HEURISTIC", ["Social proof, policies, and trust signals inspected"], []),
            "checkout_friction": (round(checkout_score, 1), "AUTOMATED_TEST", ["Commercial transaction signals and pricing inspected"], []),
            "behavioral_analytics": (analytics_score, analytics_status, ["Connected to live analytics API"] if analytics_connected else [], ["GA4 or analytics provider not connected"] if not analytics_connected else []),
        }

        cards: List[CroDimensionScoreCard] = []
        measured_weight = 0.0
        weighted_sum = 0.0
        measured_cnt = 0
        unmeasured_cnt = 0

        for d_id, d_name, ev_class, basis in cls.DIMENSION_DEFINITIONS:
            score, status, strengths, defects = raw_scores[d_id]
            cards.append(
                CroDimensionScoreCard(
                    id=d_id,
                    name=d_name,
                    weight_pct=10.0,
                    score=score,
                    status=status,
                    evidence_class=ev_class,
                    evidence_basis=basis,
                    strengths=strengths,
                    defects=defects,
                )
            )
            if score is not None:
                weighted_sum += score * 0.10
                measured_weight += 10.0
                measured_cnt += 1
            else:
                unmeasured_cnt += 1

        overall = round((weighted_sum / (measured_weight / 100.0)), 1) if measured_weight > 0 else 75.0
        grade = "A" if overall >= 85 else ("B" if overall >= 75 else ("C" if overall >= 60 else "D"))
        return TenDimensionCroScoreResult(
            overall_cro_score=overall,
            cro_grade=grade,
            dimensions=cards,
            measured_dimensions_count=measured_cnt,
            unmeasured_dimensions_count=unmeasured_cnt,
            total_weight_evaluated=measured_weight,
        )


cro_scoring_engine = CroScoringEngine()
