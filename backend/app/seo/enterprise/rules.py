"""Versioned SEO rules and a constrained evaluator.

Expressions are names in an allowlist. They are not Python source and are never passed to eval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class UnknownExpression(ValueError):
    pass


FactCheck = Callable[[dict], bool]


def _flag(name: str) -> FactCheck:
    return lambda facts: bool(facts.get(name))


CONDITIONS: dict[str, FactCheck] = {
    "title_element_missing_or_empty": _flag("title_missing"),
    "title_duplicated_in_sample": _flag("title_duplicated"),
    "title_length_outside_diagnostic_band": _flag("title_length_diagnostic"),
    "meta_description_missing": _flag("meta_missing"),
    "meta_description_duplicated": _flag("meta_duplicated"),
    "meta_length_outside_diagnostic_band": _flag("meta_length_diagnostic"),
    "h1_missing": _flag("h1_missing"),
    "multiple_h1_observed": _flag("multiple_h1"),
    "heading_hierarchy_skip": _flag("heading_hierarchy"),
    "http_4xx_observed": _flag("http_4xx"),
    "http_5xx_observed": _flag("http_5xx"),
    "redirect_loop_observed": _flag("redirect_loop"),
    "redirect_chain_observed": _flag("redirect_chain"),
    "temporary_redirect_observed": _flag("temporary_redirect"),
    "broken_internal_link_observed": _flag("broken_internal"),
    "hostname_https_inconsistent": _flag("https_inconsistent"),
    "canonical_missing": _flag("canonical_missing"),
    "canonical_conflict": _flag("canonical_conflict"),
    "noindex_observed": _flag("noindex"),
    "soft_404_observed": _flag("soft_404"),
    "robots_unavailable": _flag("robots_unavailable"),
    "robots_disallow_all": _flag("robots_disallow_all"),
    "robots_syntax_error": _flag("robots_syntax"),
    "robots_rule_conflict": _flag("robots_conflict"),
    "sitemap_not_discovered": _flag("sitemap_missing"),
    "sitemap_url_not_eligible": _flag("sitemap_ineligible"),
    "orphan_candidate_in_scope": _flag("orphan_candidate"),
    "click_depth_high": _flag("click_depth_high"),
    "url_normalization_variant": _flag("url_variant"),
    "session_parameter_observed": _flag("session_parameter"),
    "render_parity_failed": _flag("render_parity"),
    "hreflang_invalid": _flag("hreflang_invalid"),
    "missing_alt_observed": _flag("missing_alt"),
    "image_dimensions_missing": _flag("image_dimensions"),
    "mixed_content_observed": _flag("mixed_content"),
    "schema_error_observed": _flag("schema_error"),
    "security_header_absent": _flag("security_header_absent"),
    "field_lcp_above_threshold": _flag("field_lcp"),
    "field_inp_above_threshold": _flag("field_inp"),
    "field_cls_above_threshold": _flag("field_cls"),
    "viewport_missing": _flag("viewport_missing"),
    "short_extracted_text": _flag("short_text"),
    "generic_anchor_observed": _flag("generic_anchor"),
}


def evaluate_condition(expression: str, facts: dict) -> bool:
    """Return whether an allowlisted condition holds. Unknown expressions raise."""
    check = CONDITIONS.get(expression)
    if check is None:
        raise UnknownExpression(f"Rule expression is not allowlisted: {expression}")
    return bool(check(facts))


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    version: str
    chapter: int
    subchapters: tuple[str, ...]
    expression: str
    rule_class: str
    severity: str
    issue_type: str
    evidence_requirements: tuple[str, ...]


RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition("seo.robots.unavailable", "1.0.0", 3, ("3.1",), "robots_unavailable", "mandatory", "medium", "defect", ("robots_fetch",)),
    RuleDefinition("seo.robots.disallow_all", "1.0.0", 3, ("3.1", "3.2"), "robots_disallow_all", "mandatory", "critical", "defect", ("robots_txt",)),
    RuleDefinition("seo.robots.syntax", "1.0.0", 3, ("3.1",), "robots_syntax_error", "mandatory", "medium", "defect", ("robots_txt",)),
    RuleDefinition("seo.robots.conflict", "1.0.0", 3, ("3.2",), "robots_rule_conflict", "mandatory", "high", "defect", ("robots_txt",)),
    RuleDefinition("seo.title.missing", "1.0.0", 10, ("10.1",), "title_element_missing_or_empty", "mandatory", "high", "defect", ("rendered_dom_snapshot", "page_url")),
    RuleDefinition("seo.title.duplicate", "1.0.0", 10, ("10.1", "10.5"), "title_duplicated_in_sample", "mandatory", "medium", "defect", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.title.length", "1.0.0", 10, ("10.6",), "title_length_outside_diagnostic_band", "heuristic", "info", "diagnostic", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.meta.missing", "1.0.0", 11, ("11.1",), "meta_description_missing", "recommended", "low", "defect", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.meta.duplicate", "1.0.0", 11, ("11.1",), "meta_description_duplicated", "recommended", "low", "defect", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.meta.length", "1.0.0", 11, ("11.1",), "meta_length_outside_diagnostic_band", "heuristic", "info", "diagnostic", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.heading.missing_h1", "1.0.0", 12, ("12.1",), "h1_missing", "recommended", "medium", "defect", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.heading.multiple_h1", "1.0.0", 12, ("12.1",), "multiple_h1_observed", "heuristic", "info", "diagnostic", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.heading.hierarchy", "1.0.0", 12, ("12.2",), "heading_hierarchy_skip", "recommended", "medium", "defect", ("rendered_dom_snapshot",)),
    RuleDefinition("seo.http.4xx", "1.0.0", 5, ("5.1", "5.5"), "http_4xx_observed", "mandatory", "high", "defect", ("http_response",)),
    RuleDefinition("seo.http.5xx", "1.0.0", 5, ("5.1", "5.9"), "http_5xx_observed", "mandatory", "critical", "defect", ("http_response",)),
    RuleDefinition("seo.http.loop", "1.0.0", 5, ("5.2",), "redirect_loop_observed", "mandatory", "critical", "defect", ("redirect_chain",)),
    RuleDefinition("seo.http.chain", "1.0.0", 5, ("5.2",), "redirect_chain_observed", "mandatory", "medium", "defect", ("redirect_chain",)),
    RuleDefinition("seo.http.temporary", "1.0.0", 5, ("5.3",), "temporary_redirect_observed", "conditional", "low", "diagnostic", ("redirect_chain",)),
    RuleDefinition("seo.http.broken_link", "1.0.0", 5, ("5.5", "15.4"), "broken_internal_link_observed", "mandatory", "high", "defect", ("http_response",)),
    RuleDefinition("seo.http.https", "1.0.0", 5, ("5.7", "24.2"), "hostname_https_inconsistent", "mandatory", "high", "defect", ("http_response",)),
    RuleDefinition("seo.canonical.missing", "1.0.0", 4, ("4.3",), "canonical_missing", "recommended", "medium", "defect", ("canonical_tag",)),
    RuleDefinition("seo.canonical.conflict", "1.0.0", 4, ("4.4",), "canonical_conflict", "mandatory", "high", "defect", ("canonical_tag",)),
    RuleDefinition("seo.index.noindex", "1.0.0", 4, ("4.1", "4.2", "4.6"), "noindex_observed", "conditional", "high", "defect", ("robots_directive",)),
    RuleDefinition("seo.index.soft404", "1.0.0", 5, ("5.4",), "soft_404_observed", "conditional", "high", "defect", ("http_response", "page_template")),
    RuleDefinition("seo.sitemap.missing", "1.0.0", 7, ("7.1", "3.3"), "sitemap_not_discovered", "recommended", "info", "diagnostic", ("sitemap_discovery",)),
    RuleDefinition("seo.sitemap.ineligible", "1.0.0", 7, ("7.3", "7.4"), "sitemap_url_not_eligible", "mandatory", "medium", "defect", ("sitemap_url", "http_response")),
    RuleDefinition("seo.graph.orphan", "1.0.0", 15, ("15.2", "3.4"), "orphan_candidate_in_scope", "conditional", "medium", "defect", ("link_graph", "sitemap")),
    RuleDefinition("seo.graph.depth", "1.0.0", 6, ("6.6", "3.5", "15.8"), "click_depth_high", "conditional", "medium", "defect", ("link_graph",)),
    RuleDefinition("seo.url.variant", "1.0.0", 6, ("6.3",), "url_normalization_variant", "conditional", "medium", "defect", ("url_inventory",)),
    RuleDefinition("seo.url.session", "1.0.0", 6, ("6.4",), "session_parameter_observed", "conditional", "medium", "defect", ("url_inventory",)),
    RuleDefinition("seo.render.parity", "1.0.0", 8, ("8.1", "8.5"), "render_parity_failed", "conditional", "high", "defect", ("raw_html", "rendered_dom")),
    RuleDefinition("seo.hreflang.invalid", "1.0.0", 9, ("9.2", "9.3"), "hreflang_invalid", "conditional", "high", "defect", ("hreflang",)),
    RuleDefinition("seo.image.alt", "1.0.0", 14, ("14.2",), "missing_alt_observed", "recommended", "medium", "defect", ("image_element",)),
    RuleDefinition("seo.image.dimensions", "1.0.0", 14, ("14.5",), "image_dimensions_missing", "heuristic", "low", "diagnostic", ("image_element",)),
    RuleDefinition("seo.https.mixed", "1.0.0", 24, ("24.2", "24.3"), "mixed_content_observed", "mandatory", "high", "defect", ("resource_url",)),
    RuleDefinition("seo.schema.error", "1.0.0", 16, ("16.2", "16.3"), "schema_error_observed", "conditional", "high", "defect", ("structured_data",)),
    RuleDefinition("seo.security.header", "1.0.0", 24, ("24.4", "24.7"), "security_header_absent", "heuristic", "info", "observation", ("response_headers",)),
    RuleDefinition("seo.cwv.lcp", "1.0.0", 18, ("18.1", "18.4"), "field_lcp_above_threshold", "conditional", "medium", "defect", ("field_crux",)),
    RuleDefinition("seo.cwv.inp", "1.0.0", 18, ("18.2", "18.4"), "field_inp_above_threshold", "conditional", "medium", "defect", ("field_crux",)),
    RuleDefinition("seo.cwv.cls", "1.0.0", 18, ("18.3", "18.4"), "field_cls_above_threshold", "conditional", "medium", "defect", ("field_crux",)),
    RuleDefinition("seo.mobile.viewport", "1.0.0", 19, ("19.4",), "viewport_missing", "recommended", "medium", "defect", ("raw_html",)),
    RuleDefinition("seo.content.short_text", "1.0.0", 13, ("13.4",), "short_extracted_text", "heuristic", "info", "diagnostic", ("extracted_text",)),
    RuleDefinition("seo.link.generic_anchor", "1.0.0", 15, ("15.3",), "generic_anchor_observed", "heuristic", "info", "diagnostic", ("anchor_text",)),
)

RULE_BY_ID = {rule.rule_id: rule for rule in RULES}
