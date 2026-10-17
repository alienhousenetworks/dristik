"""
Dristik Modular Monolith: SEO Intelligence Domain.

Consolidates all SEO capabilities:
- Domain Pillar: SeoPillar, SEO_SPECIALISTS, build_seo_agents
- Specialist Agents: TechnicalSeoAgent, ContentSeoAgent, InternalLinkingAgent,
  StructuredDataAgent, PerformanceAgent, SpecializedSeoAgent
- Algorithmic Analyzers: Canonical, Headings, Redirects, HTTP Status, Link Depth,
  Media Assets, Meta Rollups, Rendering Disparity, Schema, SERP, Sitemap, Topical Authority
- Reporting & Publishing: CompleteSeoReportGenerator, SeoAuditBookRenderer,
  render_seo_audit_book, print reports, and Jinja2 report templates
- Audit Engine: SEOAuditOrchestrator, AuditDAG, ScoreEngine
"""
from app.seo.pillar import SeoPillar
from app.seo.specialists import SEO_SPECIALISTS, build_seo_agents
from app.seo.agents import (
    TechnicalSeoAgent,
    ContentSeoAgent,
    InternalLinkingAgent,
    StructuredDataAgent,
    PerformanceAgent,
    SpecializedSeoAgent,
)
from app.seo.analyzers import (
    analyze_canonicals,
    analyze_meta_rollup,
    analyze_heading_hierarchy,
    analyze_media_assets,
    analyze_link_depth_and_orphans,
    analyze_schema_rich_results,
    analyze_local_seo,
    analyze_international_seo,
    analyze_topical_authority,
    analyze_ecommerce_seo,
    analyze_serp_appearance,
    analyze_rendering_disparity,
    probe_host_and_redirects,
    analyze_http_statuses,
)
from app.seo.reporting import (
    CompleteSeoReportGenerator,
    seo_report_generator,
    render_seo_audit_book,
    seo_audit_book_renderer,
)
from app.seo.audit import (
    SEOAuditOrchestrator,
    execute_audit_pipeline,
)

__all__ = [
    # Pillar
    "SeoPillar",
    "SEO_SPECIALISTS",
    "build_seo_agents",
    # Agents
    "TechnicalSeoAgent",
    "ContentSeoAgent",
    "InternalLinkingAgent",
    "StructuredDataAgent",
    "PerformanceAgent",
    "SpecializedSeoAgent",
    # Analyzers
    "analyze_canonicals",
    "analyze_meta_rollup",
    "analyze_heading_hierarchy",
    "analyze_media_assets",
    "analyze_link_depth_and_orphans",
    "analyze_schema_rich_results",
    "analyze_local_seo",
    "analyze_international_seo",
    "analyze_topical_authority",
    "analyze_ecommerce_seo",
    "analyze_serp_appearance",
    "analyze_rendering_disparity",
    "probe_host_and_redirects",
    "analyze_http_statuses",
    # Reporting
    "CompleteSeoReportGenerator",
    "seo_report_generator",
    "render_seo_audit_book",
    "seo_audit_book_renderer",
    # Audit
    "SEOAuditOrchestrator",
    "execute_audit_pipeline",
]
