"""
Dristik Modular Monolith: Generative Engine Optimization (GEO) Domain Module.

Centralizes all GEO capabilities:
- Multi-engine search adapters (OpenAI Search, Claude, Perplexity, Gemini, Groq)
- Real-time LLM querying, passage extractability, and citation provenance
- Autonomous reasoning agents (GeoReadinessAgent, AiSearchCitationAgent, etc.)
- Domain pillar wave execution and deterministic scoring
- Knowledge graph, conversational question graph, and causal gap analysis
- Executive report generation, visual scorecards, and audit books
"""
from app.geo.pillar import GeoPillar, GEO_SPECIALISTS, build_geo_agents
from app.geo.citation_models import citation_catalog, active_engine_names, unqueried_surfaces
from app.geo.agents import (
    GeoReadinessAgent,
    AiSearchCitationAgent,
    PerEngineEvaluatorAgent,
    InformationGainAgent,
)
from app.geo.pipeline_runner import geo_pipeline_runner, FIXED_PROMPT_SET
from app.geo.pipeline_store import geo_pipeline_store, GeoSnapshotSummary, GeoSnapshotDetail
from app.geo.citation_gap import geo_citation_gap_engine, CausalCitationGapReport
from app.geo.benchmark_generator import benchmark_generator, BenchmarkSuite
from app.geo.benchmark_runner import benchmark_runner, ShareOfModelMetric, EvaluatedQueryRun
from app.geo.crawler_logs import crawler_log_analyzer, CrawlerLogAnalysis
from app.geo.sentiment_engine import geo_sentiment_engine, HallucinationAuditReport
from app.geo.reporting.geo_report_generator import CompleteGeoReportGenerator
from app.geo.reporting.geo_audit_book import render_geo_audit_book, geo_cover_figure
from app.geo.scoring import calculate_geo_readiness, GeoMetricsCalculator
from app.geo.dynamic_sandbox import DynamicQuestionSandboxEngine

__all__ = [
    "GeoPillar",
    "GEO_SPECIALISTS",
    "build_geo_agents",
    "citation_catalog",
    "active_engine_names",
    "unqueried_surfaces",
    "GeoReadinessAgent",
    "AiSearchCitationAgent",
    "PerEngineEvaluatorAgent",
    "InformationGainAgent",
    "geo_pipeline_runner",
    "FIXED_PROMPT_SET",
    "geo_pipeline_store",
    "GeoSnapshotSummary",
    "GeoSnapshotDetail",
    "geo_citation_gap_engine",
    "CausalCitationGapReport",
    "benchmark_generator",
    "BenchmarkSuite",
    "benchmark_runner",
    "ShareOfModelMetric",
    "EvaluatedQueryRun",
    "crawler_log_analyzer",
    "CrawlerLogAnalysis",
    "geo_sentiment_engine",
    "HallucinationAuditReport",
    "CompleteGeoReportGenerator",
    "render_geo_audit_book",
    "geo_cover_figure",
    "calculate_geo_readiness",
    "GeoMetricsCalculator",
    "DynamicQuestionSandboxEngine",
]
