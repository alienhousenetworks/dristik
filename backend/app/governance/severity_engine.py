"""Phase 12.4: Central Severity & Remediation Priority Governance Engine.

Evaluates multi-factor defect severity strictly decoupled from operational remediation priority:
- Defect Scope
- Technical Consequence
- User Impact
- Business Importance
- Search Impact
- Security Relevance
- Frequency
- Confidence
"""
from __future__ import annotations

from typing import Any, Optional

from app.governance.models import (
    RemediationPriority,
    SeverityEvaluation,
    SeverityFactor,
)


SCOPE_WEIGHTS: dict[str, float] = {
    "SITEWIDE": 1.0,
    "TEMPLATE_CLUSTER": 0.7,
    "SINGLE_PAGE": 0.3,
}

TRAFFIC_TIER_WEIGHTS: dict[str, float] = {
    "HIGH": 1.0,      # Primary landing, homepage, checkout, lead generation
    "MEDIUM": 0.6,    # Subcategory, informational article
    "LOW": 0.3,       # Legal, privacy policy, archive
    "ORPHAN": 0.1,    # Zero internal links, unindexed utility page
}


class CentralSeverityEngine:
    """Calculates objective severity and decouples it from business remediation priority."""

    def evaluate_severity_and_priority(
        self,
        finding_id: str,
        factors: SeverityFactor,
        traffic_tier: str = "MEDIUM",
        title: Optional[str] = None,
    ) -> SeverityEvaluation:
        # 1. Compute raw technical/security severity (0 - 100)
        c_tech = max(0.0, min(1.0, factors.technical_consequence))
        s_search = max(0.0, min(1.0, factors.search_impact))
        s_sec = max(0.0, min(1.0, factors.security_relevance))
        u_user = max(0.0, min(1.0, factors.user_impact))
        c_conf = max(0.0, min(1.0, factors.confidence))

        # Core technical severity formula
        raw_sev = (
            0.25 * c_tech
            + 0.20 * s_search
            + 0.20 * s_sec
            + 0.20 * u_user
            + 0.15 * c_conf
        ) * 100.0
        raw_sev = round(raw_sev, 1)

        # Map to discrete severity tier
        if raw_sev >= 80.0:
            sev_level = "CRITICAL"
        elif raw_sev >= 60.0:
            sev_level = "HIGH"
        elif raw_sev >= 40.0:
            sev_level = "MEDIUM"
        elif raw_sev >= 20.0:
            sev_level = "LOW"
        else:
            sev_level = "INFO"

        # 2. Compute Remediation Priority (Decoupled from raw severity)
        scope_w = SCOPE_WEIGHTS.get(factors.defect_scope.upper(), 0.5)
        traffic_w = TRAFFIC_TIER_WEIGHTS.get(traffic_tier.upper(), 0.5)
        bus_imp = max(0.0, min(1.0, factors.business_importance))

        # Priority score combines severity with breadth and business exposure
        priority_score = raw_sev * scope_w * traffic_w * (0.5 + 0.5 * bus_imp)

        if priority_score >= 50.0:
            rem_priority = RemediationPriority.P1
            p_desc = "P1 (Immediate Blocker — Severe impact on high-traffic business pathways)"
        elif priority_score >= 30.0:
            rem_priority = RemediationPriority.P2
            p_desc = "P2 (High Urgency — Significant impact on commercial templates)"
        elif priority_score >= 15.0:
            rem_priority = RemediationPriority.P3
            p_desc = "P3 (Scheduled Sprint — Standard backlog engineering improvement)"
        elif priority_score >= 5.0:
            rem_priority = RemediationPriority.P4
            p_desc = "P4 (Routine Maintenance — Low exposure or localized defect)"
        else:
            rem_priority = RemediationPriority.P5
            p_desc = "P5 (Low Impact — Minor defect on isolated/orphan URL)"

        explanation = (
            f"Technical Severity: {sev_level} ({raw_sev}/100) based on consequence={c_tech}, "
            f"search_impact={s_search}, security={s_sec}. "
            f"Remediation Priority: {rem_priority.value} (Score={priority_score:.1f}) based on "
            f"scope={factors.defect_scope} and traffic_tier={traffic_tier}."
        )

        return SeverityEvaluation(
            finding_id=finding_id,
            raw_severity_score=raw_sev,
            severity_level=sev_level,
            remediation_priority=rem_priority,
            explanation=explanation,
        )
