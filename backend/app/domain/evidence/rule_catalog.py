"""Machine-readable deterministic rule catalog and shared Phase 1 hygiene predicates.

Every audit rule declares:
- rule_id: canonical identifier
- input: observed signal or DOM/HTTP attribute
- threshold: pass/fail boundary
- applicable_site_types: site archetypes where the rule applies
- standard_version: governing WCAG / Google Search Central / Schema.org standard
- owning_chapter: single canonical PDF chapter that renders the full finding card
- connector_dependency: connector needed to verify real-world impact (or None)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    input: str
    threshold: str
    applicable_site_types: tuple[str, ...]
    standard_version: str
    owning_chapter: str
    connector_dependency: Optional[str] = None


RULE_CATALOG: Dict[str, RuleSpec] = {
    "TITLE_MISSING_001": RuleSpec(
        rule_id="TITLE_MISSING_001",
        input="html.<title>",
        threshold="len(title.strip()) > 0",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "TITLE_DUPLICATE_001": RuleSpec(
        rule_id="TITLE_DUPLICATE_001",
        input="html.<title> across crawled URLs",
        threshold="count(normalized_title) == 1",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "TITLE_LENGTH_001": RuleSpec(
        rule_id="TITLE_LENGTH_001",
        input="len(html.<title>)",
        threshold="25 <= len <= 65 chars",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "META_DESC_MISSING_001": RuleSpec(
        rule_id="META_DESC_MISSING_001",
        input="html.meta[name=description]",
        threshold="len(content.strip()) > 0",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "H1_MISSING_001": RuleSpec(
        rule_id="H1_MISSING_001",
        input="html.<h1>",
        threshold="count(visible_h1) >= 1",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025 / WCAG 2.2 AA",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "H1_MULTIPLE_001": RuleSpec(
        rule_id="H1_MULTIPLE_001",
        input="html.<h1>",
        threshold="count(visible_h1) == 1",
        applicable_site_types=("all",),
        standard_version="HTML Living Standard / WCAG 2.2 AA",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "STATUS_4XX_5XX_001": RuleSpec(
        rule_id="STATUS_4XX_5XX_001",
        input="http.status_code",
        threshold="status_code < 400",
        applicable_site_types=("all",),
        standard_version="RFC 9110 / Google Search Central 2025",
        owning_chapter="crawl",
        connector_dependency=None,
    ),
    "TTFB_P1": RuleSpec(
        rule_id="TTFB_P1",
        input="http.ttfb_ms (excluding unmeasured <= 0ms)",
        threshold="ttfb_ms <= 800ms",
        applicable_site_types=("all",),
        standard_version="Core Web Vitals / web.dev 2025",
        owning_chapter="crawl",
        connector_dependency="PageSpeed/CrUX",
    ),
    "CANONICAL_MISSING_001": RuleSpec(
        rule_id="CANONICAL_MISSING_001",
        input="html.link[rel=canonical]",
        threshold="present & absolute HTTPS URL",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "CANONICAL_BROKEN_001": RuleSpec(
        rule_id="CANONICAL_BROKEN_001",
        input="canonical_target.http_status",
        threshold="status_code == 200",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="seo",
        connector_dependency="Search Console",
    ),
    "SCHEMA_MISSING_001": RuleSpec(
        rule_id="SCHEMA_MISSING_001",
        input="json_ld (raw_schema + schema_types)",
        threshold="len(entities) >= 1",
        applicable_site_types=("all",),
        standard_version="Schema.org / Google Rich Results 2025",
        owning_chapter="geo",
        connector_dependency="Live AI/AEO",
    ),
    "CLICK_DEPTH_001": RuleSpec(
        rule_id="CLICK_DEPTH_001",
        input="internal_link_graph BFS depth (HTML pages only; requires edges > 0)",
        threshold="depth <= 3",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="crawl",
        connector_dependency="Search Console",
    ),
    "SITEMAP_ORPHAN_001": RuleSpec(
        rule_id="SITEMAP_ORPHAN_001",
        input="sitemap HTML URLs vs internal_link_graph inlinks (requires edges > 0)",
        threshold="inlinks >= 1",
        applicable_site_types=("all",),
        standard_version="Google Search Central 2025",
        owning_chapter="crawl",
        connector_dependency="Search Console",
    ),
    "LOCAL_SEO_NAP_001": RuleSpec(
        rule_id="LOCAL_SEO_NAP_001",
        input="NAP phones/addresses (gated on LocalBusiness schema, address, GBP, or local pages)",
        threshold="unique_valid_phones <= 1 and unique_addresses <= 1",
        applicable_site_types=("local_business", "multi_location"),
        standard_version="Google Business Profile / Local SEO 2025",
        owning_chapter="seo",
        connector_dependency="GBP/Bing",
    ),
    "WCAG_4_1_2_ACCESSIBLE_NAMES": RuleSpec(
        rule_id="WCAG_4_1_2_ACCESSIBLE_NAMES",
        input="button/link accessible name (text, aria-label, aria-labelledby, title, img[alt], svg>title)",
        threshold="non-empty accessible name",
        applicable_site_types=("all",),
        standard_version="WCAG 2.2 A",
        owning_chapter="cro",
        connector_dependency="GA4",
    ),
    "CRO_PRIMARY_CTA_001": RuleSpec(
        rule_id="CRO_PRIMARY_CTA_001",
        input="hero/page CTA controls (excluding skip links)",
        threshold=">= 1 functional non-skip primary CTA",
        applicable_site_types=("all",),
        standard_version="Dristik CRO Heuristic v4",
        owning_chapter="cro",
        connector_dependency="GA4",
    ),
}


_NON_HTML_EXTENSIONS = (
    ".xml", ".xml.gz", ".gz", ".json", ".txt", ".pdf", ".rss", ".atom",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".svg", ".ico",
    ".css", ".js", ".map", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".webm", ".mp3", ".zip",
)

_NON_HTML_FILENAMES = {
    "robots.txt",
    "sitemap.xml",
    "sitemap_index.xml",
    "ads.txt",
    "app-ads.txt",
    "llms.txt",
    "humans.txt",
    "manifest.json",
    "feed",
}


def is_non_html_utility_url(url: str) -> bool:
    """Return True for utility/machine/asset URLs (sitemap.xml, robots.txt, non-HTML assets)."""
    if not url or not isinstance(url, str):
        return True
    parsed = urlparse(url.strip())
    path = (parsed.path or "").lower().rstrip("/")
    basename = path.rsplit("/", 1)[-1] if path else ""
    if basename in _NON_HTML_FILENAMES:
        return True
    if "sitemap" in basename and (basename.endswith(".xml") or basename.endswith(".xml.gz")):
        return True
    return any(path.endswith(ext) for ext in _NON_HTML_EXTENSIONS)


_SKIP_LINK_TEXT_RE = re.compile(
    r"^\s*skip\s+(?:to\s+)?(?:main\s+)?(?:content|navigation|nav|footer|search|products?)\s*$",
    re.IGNORECASE,
)

_SKIP_HREF_RE = re.compile(r"^#(?:main|content|main-content|maincontent|primary|page-content|skip)\b", re.IGNORECASE)


def is_skip_link(text: str = "", href: str = "", classes: str = "") -> bool:
    """Return True when an anchor/control is an accessibility skip-navigation link, not a CTA."""
    clean_text = re.sub(r"\s+", " ", (text or "")).strip()
    if clean_text and _SKIP_LINK_TEXT_RE.match(clean_text):
        return True
    clean_href = (href or "").strip()
    if clean_href and _SKIP_HREF_RE.match(clean_href):
        return True
    cls_low = (classes or "").lower()
    if any(tok in cls_low for tok in ("skip-link", "skip-to-content", "skiplink", "skip_link")):
        return True
    return False


def list_rules() -> List[Dict[str, Any]]:
    """Return all registered rules as plain dicts for diagnostics and testing."""
    return [
        {
            "rule_id": spec.rule_id,
            "input": spec.input,
            "threshold": spec.threshold,
            "applicable_site_types": list(spec.applicable_site_types),
            "standard_version": spec.standard_version,
            "owning_chapter": spec.owning_chapter,
            "connector_dependency": spec.connector_dependency,
        }
        for spec in RULE_CATALOG.values()
    ]


def build_algo_trace(
    rule_id: str,
    observed_value: Any,
    status: str,
    input_override: Optional[str] = None,
    threshold_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a single normalized algorithm-trace row for the 5-point finding card."""
    spec = RULE_CATALOG.get(rule_id)
    return {
        "rule_id": rule_id,
        "input": input_override or (spec.input if spec else "observed_signal"),
        "threshold": threshold_override or (spec.threshold if spec else "policy_threshold"),
        "observed": str(observed_value),
        "status": str(status).upper(),
    }
