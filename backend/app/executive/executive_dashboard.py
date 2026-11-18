"""
Executive Decision Dashboard — Executive Intelligence (Phase 2.5)

Assembles the complete 10-point Executive Decision Dashboard:
1. Business Profile (Verified facts, commercial model)
2. Audit Scope & Coverage (Discovered vs. inspected URLs, crawl profile)
3. Verified Critical Risks (P0 blockers requiring immediate attention)
4. Top Growth Opportunities (Highest ROI opportunities)
5. Cross-Discipline Overlap (Root causes spanning SEO, AEO, and CRO)
6. Resource Requirements (Hours/days by role: DevOps, Full-stack, Content)
7. Strategic Priorities (3 executive directives)
8. 30/60/90-Day Tactical Plan (Sequenced execution roadmap)
9. Data Limitations (Explicit disclosure of unmeasured metrics/connectors)
10. Historical Performance Tracking (Comparison to prior audits or baseline)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.executive.business_intelligence import VerifiedBusinessProfile
from app.executive.three_perspective import ThreePerspectiveDiagnostic
from app.executive.business_impact import FindingBusinessImpact, TechnicalSeverity
from app.executive.opportunity_engine import StrategicOpportunity


class RoleResourceEstimate(BaseModel):
    role_name: str
    estimated_hours: float
    key_responsibilities: List[str] = Field(default_factory=list)


class TacticalRoadmapPhase(BaseModel):
    timeframe: str  # "First 30 Days", "Day 31–60", "Day 61–90"
    focus_objective: str
    milestones: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)


class ExecutiveDashboardReport(BaseModel):
    # 1. Business Profile
    business_profile: VerifiedBusinessProfile
    # 2. Audit Scope & Coverage
    audit_scope: Dict[str, Any]
    # 3. Verified Critical Risks
    critical_risks: List[FindingBusinessImpact]
    # 4. Top Growth Opportunities
    growth_opportunities: List[StrategicOpportunity]
    # 5. Cross-Discipline Overlap
    cross_discipline_overlaps: List[Dict[str, Any]]
    # 6. Resource Requirements
    resource_allocation: List[RoleResourceEstimate]
    total_estimated_hours: float
    # 7. Strategic Priorities
    strategic_priorities: List[str]
    # 8. 30/60/90-Day Tactical Plan
    tactical_roadmap: List[TacticalRoadmapPhase]
    # 9. Data Limitations
    data_limitations: List[str]
    # 10. Historical Tracking
    historical_tracking: Dict[str, Any]

    # Additional contextual perspectives
    perspective_diagnostics: Optional[ThreePerspectiveDiagnostic] = None


class ExecutiveDashboardBuilder:
    """
    Builds the 10-point Executive Decision Dashboard.
    """

    @classmethod
    def assemble_dashboard(
        cls,
        business_profile: VerifiedBusinessProfile,
        discovered_urls_count: int,
        crawled_urls_count: int,
        crawl_profile: str,
        evaluated_impacts: List[FindingBusinessImpact],
        opportunities: List[StrategicOpportunity],
        perspective_diagnostics: Optional[ThreePerspectiveDiagnostic] = None,
        prior_audit_scores: Optional[Dict[str, float]] = None,
        current_scores: Optional[Dict[str, float]] = None,
        analytics_connected: bool = False,
    ) -> ExecutiveDashboardReport:
        # 1. Scope & Coverage
        coverage_pct = round((crawled_urls_count / max(discovered_urls_count, 1)) * 100, 1)
        audit_scope = {
            "discovered_urls": discovered_urls_count,
            "inspected_urls": crawled_urls_count,
            "crawl_profile": crawl_profile,
            "coverage_percentage": f"{coverage_pct}%",
            "scope_statement": f"Inspected {crawled_urls_count} high-priority pages from {discovered_urls_count} discovered URLs using the {crawl_profile} profile.",
        }

        # 2. Critical Risks (P0/Critical technical severity)
        crit_risks = [
            f for f in evaluated_impacts
            if f.technical_severity in (TechnicalSeverity.CRITICAL, TechnicalSeverity.HIGH)
        ][:5]

        # 3. Top Opportunities
        top_opps = opportunities[:4]

        # 4. Cross-Discipline Overlap
        cross_overlaps = [
            {
                "issue_theme": "Schema & Entity Semantic Grounding",
                "disciplines_affected": ["SEO", "AEO"],
                "business_rationale": "Missing Organization and AggregateRating schema hurts both search snippet CTR and AI engine quotation eligibility.",
            },
            {
                "issue_theme": "Server Response Latency (TTFB)",
                "disciplines_affected": ["SEO", "CRO"],
                "business_rationale": "High initial server latency burns crawl budget while triggering initial user abandonment on mobile connections.",
            },
            {
                "issue_theme": "Value Proposition Clarity & Callout Microcopy",
                "disciplines_affected": ["AEO", "CRO"],
                "business_rationale": "Vague hero copy prevents LLM direct attribution and confuses prospective first-time human buyers.",
            },
        ]

        # 5. Resource Requirements (DevOps, Full-stack, Content)
        resource_allocation = [
            RoleResourceEstimate(
                role_name="Infrastructure & DevOps",
                estimated_hours=12.0,
                key_responsibilities=[
                    "Configure edge caching and CDN optimization for TTFB stability",
                    "Harmonize server-side redirects and canonical HTTP headers",
                ],
            ),
            RoleResourceEstimate(
                role_name="Full-Stack Engineering",
                estimated_hours=24.0,
                key_responsibilities=[
                    "Implement validated Schema.org JSON-LD (Organization, Product, FAQ)",
                    "Streamline checkout form validation and add express payment options",
                ],
            ),
            RoleResourceEstimate(
                role_name="Content & Brand Strategy",
                estimated_hours=16.0,
                key_responsibilities=[
                    "Produce comparison landing pages for bottom-funnel organic search",
                    "Rewrite product headlines to emphasize verified clinical benefits",
                ],
            ),
        ]
        total_hours = sum(r.estimated_hours for r in resource_allocation)

        # 6. Strategic Priorities (3 executive directives)
        strategic_priorities = [
            "P0: Protect Core Conversion Flow — Eliminate form barriers and surface trust guarantees at checkout.",
            "P1: Fortify AI & Search Visibility — Deploy structured entity schemas and concise answer blocks across top templates.",
            "P2: Modernize Delivery Infrastructure — Eliminate TTFB latency outliers through edge HTML caching.",
        ]

        # 7. 30/60/90-Day Tactical Plan
        tactical_roadmap = [
            TacticalRoadmapPhase(
                timeframe="First 30 Days (Immediate Stabilization)",
                focus_objective="Fix conversion blockers and deploy foundational Schema.org entities.",
                milestones=[
                    "Deploy Schema.org Organization, WebSite, and Product microdata",
                    "Add return guarantee badge and streamline mobile cart fields",
                    "Resolve 404 crawl errors and unblock search spiders in robots.txt",
                ],
                deliverables=["Verified Schema Rich Results", "Frictionless Mobile Checkout Flow"],
            ),
            TacticalRoadmapPhase(
                timeframe="Day 31–60 (Authority & Coverage Expansion)",
                focus_objective="Capture commercial search intent and expand answer-engine citation readiness.",
                milestones=[
                    "Publish 3 core competitor comparison pages",
                    "Restructure top 10 informational guides with 40-word answer definitions",
                    "Implement edge caching rules for sub-300ms global TTFB",
                ],
                deliverables=["High-Intent Comparison Hubs", "Edge-Cached High-Speed Pages"],
            ),
            TacticalRoadmapPhase(
                timeframe="Day 61–90 (Systemic Differentiation)",
                focus_objective="Scale topical authority and continuous regression auditing.",
                milestones=[
                    "Establish automated weekly verification crawls against core landing pages",
                    "Conduct customer A/B testing on reworked value propositions",
                    "Monitor weekly generative search citation share across Gemini, ChatGPT, and Perplexity",
                ],
                deliverables=["Continuous Quality CI/CD Pipeline", "AI Citation Share Benchmark Report"],
            ),
        ]

        # 8. Data Limitations
        limitations = [
            "Audit sample represents inspected URLs and templates; uninspected deep URLs may hold unique variations.",
        ]
        if not analytics_connected:
            limitations.append(
                "Financial revenue exposure is unmeasured: Google Analytics 4 or commercial telemetry is not connected to this audit run."
            )
        limitations.append(
            "Answer-engine citations reflect live probe responses at the timestamp of inspection and can fluctuate based on model updates."
        )

        # 9. Historical Performance Tracking
        hist_tracking: Dict[str, Any] = {
            "baseline_available": bool(prior_audit_scores),
            "current_scores": current_scores or {},
            "prior_scores": prior_audit_scores or {},
            "net_score_delta": None,
        }
        if prior_audit_scores and current_scores:
            deltas = {}
            for k, cur_v in current_scores.items():
                if k in prior_audit_scores:
                    deltas[k] = round(cur_v - prior_audit_scores[k], 2)
            hist_tracking["net_score_delta"] = deltas

        return ExecutiveDashboardReport(
            business_profile=business_profile,
            audit_scope=audit_scope,
            critical_risks=crit_risks,
            growth_opportunities=top_opps,
            cross_discipline_overlaps=cross_overlaps,
            resource_allocation=resource_allocation,
            total_estimated_hours=total_hours,
            strategic_priorities=strategic_priorities,
            tactical_roadmap=tactical_roadmap,
            data_limitations=limitations,
            historical_tracking=hist_tracking,
            perspective_diagnostics=perspective_diagnostics,
        )


# Compatibility aliases
ExecutiveDashboard = ExecutiveDashboardBuilder
ExecutiveDecisionBrief = ExecutiveDashboardReport

