"""
Business Impact Model — Executive Intelligence (Phase 2.3)

Evaluates multidimensional business impact for every significant finding:
- Technical severity
- Business relevance
- User impact
- Search impact
- Financial exposure (Strict NOT_MEASURED safeguard when analytics are absent)
- Confidence
- Remediation effort
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TechnicalSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BusinessRelevance(str, Enum):
    CORE_REVENUE = "CORE_REVENUE"
    BRAND_TRUST = "BRAND_TRUST"
    CUSTOMER_ACQUISITION = "CUSTOMER_ACQUISITION"
    COMPLIANCE = "COMPLIANCE"


class UserImpact(str, Enum):
    HIGH_FRICTION = "HIGH_FRICTION"
    MODERATE_FRICTION = "MODERATE_FRICTION"
    LOW_FRICTION = "LOW_FRICTION"


class SearchImpact(str, Enum):
    DEINDEXATION_RISK = "DEINDEXATION_RISK"
    RANKING_DROP = "RANKING_DROP"
    SNIPPET_DEGRADATION = "SNIPPET_DEGRADATION"
    NEUTRAL = "NEUTRAL"


class ConfidenceLevel(str, Enum):
    STRONG = "STRONG"
    LIKELY = "LIKELY"
    UNCERTAIN = "UNCERTAIN"


class FinancialExposure(BaseModel):
    is_measured: bool = False
    status: str = "NOT_MEASURED"
    estimated_monthly_exposure_usd: Optional[float] = None
    statement: str = "Financial impact not measured. Connected revenue analytics unavailable."
    calculation_basis: Optional[str] = None


class FindingBusinessImpact(BaseModel):
    finding_id: str
    finding_title: str
    technical_severity: TechnicalSeverity
    business_relevance: BusinessRelevance
    user_impact: UserImpact
    search_impact: SearchImpact
    financial_exposure: FinancialExposure
    confidence: ConfidenceLevel
    remediation_effort: str
    priority_rank: int = 1


class BusinessImpactEvaluator:
    """
    Evaluates raw audit findings into executive-grade business impact profiles.
    Never invents or fabricates revenue numbers when analytics are absent.
    """

    @classmethod
    def evaluate_finding(
        cls,
        finding: Any,
        analytics_connected: bool = False,
        monthly_traffic: Optional[int] = None,
        average_order_value: Optional[float] = None,
        conversion_rate: Optional[float] = None,
    ) -> FindingBusinessImpact:
        finding_id = str(getattr(finding, "id", getattr(finding, "finding_id", "FND-001")))
        title = str(getattr(finding, "title", str(finding)))
        raw_sev = str(getattr(finding, "severity", "MEDIUM")).upper()

        # 1. Technical Severity
        if "CRIT" in raw_sev:
            tech_sev = TechnicalSeverity.CRITICAL
        elif "HIGH" in raw_sev:
            tech_sev = TechnicalSeverity.HIGH
        elif "LOW" in raw_sev or "INFO" in raw_sev:
            tech_sev = TechnicalSeverity.LOW
        else:
            tech_sev = TechnicalSeverity.MEDIUM

        # 2. Business Relevance
        title_lower = title.lower()
        if any(w in title_lower for w in ["cart", "checkout", "payment", "buy", "order", "price"]):
            relevance = BusinessRelevance.CORE_REVENUE
        elif any(w in title_lower for w in ["privacy", "gdpr", "consent", "terms", "legal"]):
            relevance = BusinessRelevance.COMPLIANCE
        elif any(w in title_lower for w in ["trust", "review", "testimonial", "security", "ssl", "badge"]):
            relevance = BusinessRelevance.BRAND_TRUST
        else:
            relevance = BusinessRelevance.CUSTOMER_ACQUISITION

        # 3. User Impact
        if relevance == BusinessRelevance.CORE_REVENUE or tech_sev == TechnicalSeverity.CRITICAL:
            user_imp = UserImpact.HIGH_FRICTION
        elif tech_sev == TechnicalSeverity.HIGH or "friction" in title_lower:
            user_imp = UserImpact.MODERATE_FRICTION
        else:
            user_imp = UserImpact.LOW_FRICTION

        # 4. Search Impact
        if any(w in title_lower for w in ["noindex", "robots", "canonical", "crawl", "500", "404"]):
            search_imp = SearchImpact.DEINDEXATION_RISK
        elif any(w in title_lower for w in ["title", "h1", "meta", "schema", "entity"]):
            search_imp = SearchImpact.SNIPPET_DEGRADATION
        elif tech_sev in (TechnicalSeverity.CRITICAL, TechnicalSeverity.HIGH):
            search_imp = SearchImpact.RANKING_DROP
        else:
            search_imp = SearchImpact.NEUTRAL

        # 5. Financial Exposure (Zero Fake Certainty Safeguard)
        if analytics_connected and monthly_traffic and average_order_value and conversion_rate:
            impact_factor = 0.05 if tech_sev == TechnicalSeverity.CRITICAL else 0.015
            exposure_val = round(monthly_traffic * impact_factor * conversion_rate * average_order_value, 2)
            fin_exposure = FinancialExposure(
                is_measured=True,
                status="MEASURED",
                estimated_monthly_exposure_usd=exposure_val,
                statement=f"Estimated monthly exposure of ${exposure_val:,.2f} based on verified GA4 conversion telemetry.",
                calculation_basis=f"Traffic: {monthly_traffic:,} visits, AOV: ${average_order_value:.2f}, Baseline CVR: {conversion_rate * 100:.2f}%",
            )
        else:
            fin_exposure = FinancialExposure(
                is_measured=False,
                status="NOT_MEASURED",
                estimated_monthly_exposure_usd=None,
                statement="Financial impact not measured. Connected revenue analytics unavailable.",
                calculation_basis="Requires connected Google Analytics 4, Shopify, or BigCommerce telemetry.",
            )

        # 6. Confidence Level
        evidence_status = str(getattr(finding, "evidence_status", "")).upper()
        if "OBSERVED" in evidence_status or "MEASURED" in evidence_status:
            confidence = ConfidenceLevel.STRONG
        elif "INFERRED" in evidence_status:
            confidence = ConfidenceLevel.UNCERTAIN
        else:
            confidence = ConfidenceLevel.LIKELY

        # 7. Remediation Effort
        if tech_sev == TechnicalSeverity.CRITICAL:
            effort = "1–2 days"
        elif tech_sev == TechnicalSeverity.HIGH:
            effort = "3–5 days" if "architecture" in title_lower or "migration" in title_lower else "4–8 hours"
        else:
            effort = "2–4 hours"

        # 8. Priority Rank
        rank = 1 if tech_sev == TechnicalSeverity.CRITICAL else (2 if tech_sev == TechnicalSeverity.HIGH else 3)

        return FindingBusinessImpact(
            finding_id=finding_id,
            finding_title=title,
            technical_severity=tech_sev,
            business_relevance=relevance,
            user_impact=user_imp,
            search_impact=search_imp,
            financial_exposure=fin_exposure,
            confidence=confidence,
            remediation_effort=effort,
            priority_rank=rank,
        )

    @classmethod
    def evaluate_batch(
        cls,
        findings: List[Any],
        analytics_connected: bool = False,
        monthly_traffic: Optional[int] = None,
        average_order_value: Optional[float] = None,
        conversion_rate: Optional[float] = None,
    ) -> List[FindingBusinessImpact]:
        results = [
            cls.evaluate_finding(
                f,
                analytics_connected=analytics_connected,
                monthly_traffic=monthly_traffic,
                average_order_value=average_order_value,
                conversion_rate=conversion_rate,
            )
            for f in findings
        ]
        # Sort by priority rank ascending (1 = highest)
        results.sort(key=lambda x: (x.priority_rank, x.technical_severity != TechnicalSeverity.CRITICAL))
        return results


# Compatibility aliases
BusinessImpactModel = BusinessImpactEvaluator
BusinessImpactScore = FindingBusinessImpact
