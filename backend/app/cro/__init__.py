"""
Dristik Modular Monolith: Conversion Rate Optimization (CRO) & UX Intelligence Domain.

Consolidates all CRO capabilities:
- Domain Pillar: CroPillar, CRO_SPECIALISTS, build_cro_agents, evaluate_friction
- Specialist Agents: CroConversionAgent, VisualUxFrictionAgent, FormAbandonmentAgent, PricingTrustAgent
- Algorithmic Analyzers: CroAnalyzer, analyze_cro, generate_agentic_cta_rewrite
- Intelligence & Engine: build_cro_intelligence, build_from_executive_report, CroIntelligenceReport
- Master Taxonomy & Metrics: catalog, PARTS, SPECIALISTS, APPENDICES, EVIDENCE_STATES, METRIC_CATALOG, rate
- Reporting: CroReportGenerator, cro_report_generator, render_cro_audit_book
"""
from app.cro.pillar import CroPillar, CRO_SPECIALISTS, build_cro_agents, evaluate_friction
from app.cro.agents import (
    CroConversionAgent,
    VisualUxFrictionAgent,
    FormAbandonmentAgent,
    PricingTrustAgent,
)
from app.cro.analyzer import (
    CroAnalyzer,
    analyze_cro,
    generate_agentic_cta_rewrite,
    HIGH_INTENT_PATTERNS,
    EXPLORATORY_PATTERNS,
    PASSIVE_GENERIC_PATTERNS,
)
from app.cro.engine import (
    build_cro_intelligence,
    build_from_executive_report,
    CroIntelligenceReport,
)
from app.cro.taxonomy import (
    APPENDICES,
    EVIDENCE_STATES,
    PARTS,
    REPORT_CHAPTERS,
    SCORING_DIMENSIONS,
    SPECIALISTS,
    catalog,
)
from app.cro.metrics import (
    MEASUREMENT_RULES,
    METRIC_CATALOG,
    experiment_lift,
    incremental_profit,
    rate,
)
from app.cro.reporting import (
    CroReportGenerator,
    cro_report_generator,
    render_cro_audit_book,
)
from app.cro.visual_inspector import (
    VisualInspector,
    visual_inspector,
    VIEWPORT_PROFILES,
    VIEWPORT_DISCLOSURE,
)
from app.cro.journey_mapper import JourneyMapper, journey_mapper
from app.cro.value_prop_analyzer import ValuePropAnalyzer, value_prop_analyzer
from app.cro.ecommerce_saas_analyzer import EcommerceSaasAnalyzer, ecommerce_saas_analyzer
from app.cro.accessibility.wcag_cro_integrator import WcagCroIntegrator, wcag_cro_integrator
from app.cro.behavioral_analytics import BehavioralAnalyticsEvaluator, behavioral_analytics_evaluator
from app.cro.experimentation_engine import ExperimentationEngine, experimentation_engine
from app.cro.scoring import CroScoringEngine, cro_scoring_engine
from app.cro.recommendations import RecommendationGenerator, recommendation_generator

__all__ = [
    # Pillar
    "CroPillar",
    "CRO_SPECIALISTS",
    "build_cro_agents",
    "evaluate_friction",
    # Agents
    "CroConversionAgent",
    "VisualUxFrictionAgent",
    "FormAbandonmentAgent",
    "PricingTrustAgent",
    # Analyzer
    "CroAnalyzer",
    "analyze_cro",
    "generate_agentic_cta_rewrite",
    "HIGH_INTENT_PATTERNS",
    "EXPLORATORY_PATTERNS",
    "PASSIVE_GENERIC_PATTERNS",
    # Engine & Models
    "build_cro_intelligence",
    "build_from_executive_report",
    "CroIntelligenceReport",
    # Taxonomy
    "APPENDICES",
    "EVIDENCE_STATES",
    "PARTS",
    "REPORT_CHAPTERS",
    "SCORING_DIMENSIONS",
    "SPECIALISTS",
    "catalog",
    # Metrics
    "MEASUREMENT_RULES",
    "METRIC_CATALOG",
    "experiment_lift",
    "incremental_profit",
    "rate",
    # Reporting
    "CroReportGenerator",
    "cro_report_generator",
    "render_cro_audit_book",
    # Phase 6 Core Engines
    "VisualInspector",
    "visual_inspector",
    "VIEWPORT_PROFILES",
    "VIEWPORT_DISCLOSURE",
    "JourneyMapper",
    "journey_mapper",
    "ValuePropAnalyzer",
    "value_prop_analyzer",
    "EcommerceSaasAnalyzer",
    "ecommerce_saas_analyzer",
    "WcagCroIntegrator",
    "wcag_cro_integrator",
    "BehavioralAnalyticsEvaluator",
    "behavioral_analytics_evaluator",
    "ExperimentationEngine",
    "experimentation_engine",
    "CroScoringEngine",
    "cro_scoring_engine",
    "RecommendationGenerator",
    "recommendation_generator",
]
