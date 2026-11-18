"""
Crawlability & Indexability Intelligence — Phase 3.1

Sub-phases:
- 3.1.1: Robots and crawl policy (robots.txt, UA rules, sitemaps, disallowed paths, conflicting directives, robots meta, X-Robots-Tag, blocked resources)
- 3.1.2: Indexability analysis (noindex, canonical validation, conflicts, self-referencing, redirect chains, duplicate groups, pagination, parameterized, orphans, soft 404)
- 3.1.3: URL architecture (hierarchy, depth, slug quality, parameter pollution, duplicate paths, redirect chains, HTTP/HTTPS, WWW/non-WWW, trailing slash, language/regional)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel, Field


# ============================================================================
# 3.1.1: Robots and Crawl Policy
# ============================================================================

class RobotsRule(BaseModel):
    user_agent: str
    directive: str  # "allow" or "disallow"
    path: str


class RobotsPolicyReport(BaseModel):
    has_robots_txt: bool
    sitemap_declarations: List[str] = Field(default_factory=list)
    rules: List[RobotsRule] = Field(default_factory=list)
    conflicting_directives: List[str] = Field(default_factory=list)
    blocked_critical_resources: List[str] = Field(default_factory=list)
    googlebot_allowed: bool = True
    observations: List[str] = Field(default_factory=list)


class RobotsPolicyAnalyzer:
    @classmethod
    def parse_robots_txt(
        cls,
        robots_txt_content: str,
        resource_urls: Optional[List[str]] = None,
    ) -> RobotsPolicyReport:
        if not robots_txt_content or not robots_txt_content.strip():
            return RobotsPolicyReport(
                has_robots_txt=False,
                observations=["No robots.txt file declared; search crawlers default to full crawl access."],
            )

        sitemaps: List[str] = []
        rules: List[RobotsRule] = []
        conflicts: List[str] = []
        blocked_resources: List[str] = []
        current_ua = "*"

        lines = robots_txt_content.splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, val = [p.strip() for p in line.split(":", 1)]
                key_lower = key.lower()

                if key_lower == "user-agent":
                    current_ua = val
                elif key_lower == "sitemap":
                    sitemaps.append(val)
                elif key_lower in ("disallow", "allow"):
                    rules.append(RobotsRule(user_agent=current_ua, directive=key_lower, path=val))

        # Check for conflicting directives
        paths_seen: Dict[str, Set[str]] = {}
        for r in rules:
            if r.user_agent in ("*", "Googlebot"):
                if r.path not in paths_seen:
                    paths_seen[r.path] = set()
                paths_seen[r.path].add(r.directive)
        
        for p, dirs in paths_seen.items():
            if len(dirs) > 1 and p != "":
                conflicts.append(f"Conflicting Allow/Disallow rule for path: '{p}'")

        # Check for blocked critical resources (CSS, JS)
        resources = resource_urls or []
        for res in resources:
            for r in rules:
                if r.directive == "disallow" and r.path and r.path in res:
                    if any(res.endswith(ext) for ext in [".css", ".js", ".mjs"]):
                        blocked_resources.append(res)
                        break

        # Check googlebot access
        googlebot_blocked = any(
            r.user_agent.lower() in ("googlebot", "*") and r.directive == "disallow" and r.path in ("/", "/*")
            for r in rules
        )

        obs = [
            f"Parsed {len(rules)} directives across declared user agents.",
            f"Found {len(sitemaps)} sitemap reference(s).",
        ]
        if googlebot_blocked:
            obs.append("CRITICAL: Root path is disallowed for Googlebot or general crawlers.")

        return RobotsPolicyReport(
            has_robots_txt=True,
            sitemap_declarations=sitemaps,
            rules=rules,
            conflicting_directives=conflicts,
            blocked_critical_resources=list(set(blocked_resources)),
            googlebot_allowed=not googlebot_blocked,
            observations=obs,
        )


# ============================================================================
# 3.1.2: Indexability Analysis
# ============================================================================

class PageIndexabilityResult(BaseModel):
    url: str
    is_indexable: bool
    status_code: int
    noindex_detected: bool
    noindex_source: Optional[str] = None  # "HTML_META" or "X_ROBOTS_TAG"
    canonical_url: Optional[str] = None
    is_self_canonical: bool = True
    canonical_conflict: Optional[str] = None
    is_soft_404: bool = False
    is_orphan: bool = False
    reasons_non_indexable: List[str] = Field(default_factory=list)


class IndexabilityAnalyzer:
    @classmethod
    def evaluate_page(
        cls,
        url: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        html: str = "",
        canonical_tag: Optional[str] = None,
        inbound_links_count: int = 1,
    ) -> PageIndexabilityResult:
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        reasons: List[str] = []
        noindex = False
        noindex_src = None

        # 1. Status Code
        if status_code != 200:
            reasons.append(f"HTTP status is {status_code} (non-200).")

        # 2. X-Robots-Tag Header
        x_robots = hdrs.get("x-robots-tag", "").lower()
        if "noindex" in x_robots:
            noindex = True
            noindex_src = "X_ROBOTS_TAG"
            reasons.append("X-Robots-Tag response header contains 'noindex'.")

        # 3. HTML Meta Robots
        meta_match = re.search(r'<meta[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if meta_match:
            content = meta_match.group(1).lower()
            if "noindex" in content:
                noindex = True
                noindex_src = "HTML_META"
                reasons.append("HTML <meta name='robots'> contains 'noindex'.")

        # 4. Canonical Evaluation
        is_self_can = True
        canonical_conflict = None
        clean_url = url.split("?")[0].rstrip("/")
        if canonical_tag:
            clean_can = canonical_tag.split("?")[0].rstrip("/")
            if clean_can and clean_can != clean_url:
                is_self_can = False
                canonical_conflict = f"Canonicalized to alternate destination: {canonical_tag}"
                reasons.append(f"Points canonical to external/alternate URL: {canonical_tag}")

        # 5. Soft 404 Detection
        is_soft_404 = False
        if status_code == 200:
            low_html = html.lower()
            if any(phrase in low_html for phrase in ["page not found", "404 not found", "item does not exist", "product unavailable"]):
                if len(html.strip()) < 1500 or "not found" in low_html[:500]:
                    is_soft_404 = True
                    reasons.append("Detected Soft 404: Returns 200 OK but content indicates missing page.")

        # 6. Orphan Check
        is_orphan = inbound_links_count == 0
        if is_orphan:
            reasons.append("Orphan page: Discovered in sitemap/input but has zero internal inbound links.")

        is_indexable = (status_code == 200) and (not noindex) and is_self_can and (not is_soft_404)

        return PageIndexabilityResult(
            url=url,
            is_indexable=is_indexable,
            status_code=status_code,
            noindex_detected=noindex,
            noindex_source=noindex_src,
            canonical_url=canonical_tag,
            is_self_canonical=is_self_can,
            canonical_conflict=canonical_conflict,
            is_soft_404=is_soft_404,
            is_orphan=is_orphan,
            reasons_non_indexable=reasons,
        )


# ============================================================================
# 3.1.3: URL Architecture
# ============================================================================

class UrlArchitectureReport(BaseModel):
    url: str
    folder_depth: int
    slug: str
    slug_quality_score: float  # 0.0 to 1.0
    has_parameter_pollution: bool
    parameters_found: List[str] = Field(default_factory=list)
    has_trailing_slash: bool
    is_https: bool
    is_www: bool
    language_prefix: Optional[str] = None
    architectural_defects: List[str] = Field(default_factory=list)


class UrlArchitectureAuditor:
    @classmethod
    def audit_url(cls, url: str) -> UrlArchitectureReport:
        parsed = urlparse(url)
        path = parsed.path or "/"
        defects: List[str] = []

        # 1. Depth & Slug
        segments = [s for s in path.split("/") if s]
        depth = len(segments)
        slug = segments[-1] if segments else ""

        # 2. Slug Quality
        slug_score = 1.0
        if "_" in slug:
            slug_score -= 0.2
            defects.append("Slug uses underscores instead of hyphens.")
        if any(c.isupper() for c in slug):
            slug_score -= 0.2
            defects.append("Slug contains uppercase characters.")
        if len(slug) > 80:
            slug_score -= 0.3
            defects.append("Excessively long slug (>80 characters).")
        if depth > 4:
            defects.append(f"Excessive folder depth ({depth} levels). Recommend flattening hierarchy.")

        # 3. Parameter Pollution
        params = list(parse_qs(parsed.query).keys())
        has_pollution = any(p.startswith("utm_") or p in ("gclid", "fbclid", "sessionid", "phpsessid") for p in params)
        if has_pollution:
            defects.append("Tracking or session parameters present in canonical URL.")

        # 4. Trailing Slash Consistency
        has_slash = path.endswith("/") if path != "/" else True

        # 5. HTTPS and Host
        is_https = parsed.scheme.lower() == "https"
        if not is_https:
            defects.append("Insecure HTTP protocol used in URL.")
        is_www = parsed.netloc.lower().startswith("www.")

        # 6. Language Prefix
        lang_match = re.match(r"^/([a-z]{2}(?:-[a-z]{2})?)/", path)
        lang_prefix = lang_match.group(1) if lang_match else None

        return UrlArchitectureReport(
            url=url,
            folder_depth=depth,
            slug=slug,
            slug_quality_score=max(0.0, round(slug_score, 2)),
            has_parameter_pollution=has_pollution,
            parameters_found=params,
            has_trailing_slash=has_slash,
            is_https=is_https,
            is_www=is_www,
            language_prefix=lang_prefix,
            architectural_defects=defects,
        )
