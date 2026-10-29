"""
Dristik General & Specialized Analyzers.

Technical SEO analyzers are consolidated into `app.seo.analyzers` and CRO into `app.cro`, re-exported here for compatibility.
"""
from __future__ import annotations

import sys
import types

__path__: list[str] = []

from app.cro.form_analyzer import FormAccessibilityAnalyzer, analyze_forms
from app.crawl.analyzers.security_analyzer import analyze_security_headers, SecurityAnalyzer

_form_mod = types.ModuleType("app.analyzers.form_analyzer")
_form_mod.FormAccessibilityAnalyzer = FormAccessibilityAnalyzer
_form_mod.analyze_forms = analyze_forms
sys.modules["app.analyzers.form_analyzer"] = _form_mod

_sec_mod = types.ModuleType("app.analyzers.security_analyzer")
_sec_mod.SecurityAnalyzer = SecurityAnalyzer
_sec_mod.analyze_security_headers = analyze_security_headers
sys.modules["app.analyzers.security_analyzer"] = _sec_mod

def __getattr__(name: str):
    if name in ("CroAnalyzer", "analyze_cro"):
        from app.cro.analyzer import CroAnalyzer, analyze_cro
        return {"CroAnalyzer": CroAnalyzer, "analyze_cro": analyze_cro}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

from app.seo.analyzers import (
    CanonicalAuditor,
    analyze_canonicals,
    CanonicalRedirectConsistencyAnalyzer,
    analyze_ecommerce_seo,
    HeadingAnalyzer,
    analyze_heading_hierarchy,
    HostRedirectProber,
    probe_host_and_redirects,
    HttpStatusAuditor,
    analyze_http_statuses,
    analyze_international_seo,
    LinkDepthAnalyzer,
    analyze_link_depth_and_orphans,
    analyze_local_seo,
    MediaAssetAnalyzer,
    analyze_media_assets,
    MetaRollupAnalyzer,
    analyze_meta_rollup,
    estimate_pixel_width,
    RenderingDisparityAnalyzer,
    analyze_rendering_disparity,
    analyze_schema_rich_results,
    validate_schema_entity,
    analyze_serp_appearance,
    SitemapOrphanAnalyzer,
    analyze_topical_authority,
)

__all__ = [
    "CroAnalyzer",
    "analyze_cro",
    "FormAccessibilityAnalyzer",
    "analyze_forms",
    "analyze_security_headers",
    "SecurityAnalyzer",
    "CanonicalAuditor",
    "analyze_canonicals",
    "CanonicalRedirectConsistencyAnalyzer",
    "analyze_ecommerce_seo",
    "HeadingAnalyzer",
    "analyze_heading_hierarchy",
    "HostRedirectProber",
    "probe_host_and_redirects",
    "HttpStatusAuditor",
    "analyze_http_statuses",
    "analyze_international_seo",
    "LinkDepthAnalyzer",
    "analyze_link_depth_and_orphans",
    "analyze_local_seo",
    "MediaAssetAnalyzer",
    "analyze_media_assets",
    "MetaRollupAnalyzer",
    "analyze_meta_rollup",
    "estimate_pixel_width",
    "RenderingDisparityAnalyzer",
    "analyze_rendering_disparity",
    "analyze_schema_rich_results",
    "validate_schema_entity",
    "analyze_serp_appearance",
    "SitemapOrphanAnalyzer",
    "analyze_topical_authority",
]
