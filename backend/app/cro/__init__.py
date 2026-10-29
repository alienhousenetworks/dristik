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
]
