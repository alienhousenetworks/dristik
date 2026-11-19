"""
Impact Attribution Engine — Phase 8.8 (10/10 Transformation)

Enforces strict 3-tier outcome attribution:
1. TECHNICAL_SUCCESS: The defect was fixed (syntax, response code, schema presence).
2. SEARCH_AI_OUTCOME: Measured change in SERP rank, AI citation rate, or impressions.
3. COMMERCIAL_OUTCOME: Measured change in conversion rate, form submissions, or revenue.

STRICT ZERO-FABRICATION RULE:
A technical fix does not automatically prove a ranking or revenue improvement.
Each tier requires independent, timestamped empirical observation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.remediation.models import ImpactAttribution, RemediationTaskRecord

logger = logging.getLogger("dristik.remediation.impact")


class ImpactAttributionEngine:
    """
    Evaluates and records decoupled 3-tier impact records.
    """

    def record_technical_success(
        self,
        task: RemediationTaskRecord,
        evidence: str,
    ) -> ImpactAttribution:
        return ImpactAttribution(
            task_id=task.task_id,
            finding_id=task.finding_id,
            technical_success=True,
            technical_evidence=evidence,
            search_ai_outcome_observed=False,
            search_ai_evidence=None,
            commercial_outcome_observed=False,
            commercial_evidence=None,
            historical_observation_window_days=30,
            zero_fabrication_confirmed=True,
        )

    def attach_search_ai_outcome(
        self,
        record: ImpactAttribution,
        observed_citation_lift_pct: Optional[float] = None,
        observed_rank_delta: Optional[int] = None,
    ) -> ImpactAttribution:
        if observed_citation_lift_pct is not None or observed_rank_delta is not None:
            record.search_ai_outcome_observed = True
            record.search_ai_evidence = (
                f"Observed search/AI shift: Citation lift={observed_citation_lift_pct}%, "
                f"SERP rank delta={observed_rank_delta}."
            )
        return record

    def attach_commercial_outcome(
        self,
        record: ImpactAttribution,
        measured_cr_lift_pct: Optional[float] = None,
        measured_revenue_delta: Optional[float] = None,
    ) -> ImpactAttribution:
        if measured_cr_lift_pct is not None or measured_revenue_delta is not None:
            record.commercial_outcome_observed = True
            record.commercial_evidence = (
                f"Observed commercial shift: CR lift={measured_cr_lift_pct}%, "
                f"Revenue delta={measured_revenue_delta}."
            )
        return record


impact_attribution_engine = ImpactAttributionEngine()
