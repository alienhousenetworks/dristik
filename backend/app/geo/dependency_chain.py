"""
Four-Layer GEO Diagnostic Dependency Chain & Index Hygiene Engine.

Adapted from GeoLook's MIT-licensed four-layer model (Access -> Orientation ->
Understanding -> Quotability):
- Every layer depends on the layer above it.
- If an upstream layer fails (e.g., WAF blocks AI crawlers or SPA shells have no
  static text), downstream layers are explicitly stamped `blocked_by` and their
  effective score is withheld (`None`, never `0`).
- Also checks sitemap index pollution, exact duplicate titles, near-duplicate
  body prefixes, X-Robots-Tag noindex, schema-vs-visible-content mismatch,
  article author-entity presence, and functional-page SPA exemptions.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.crawl.robots import check_ai_bots_robots, declared_sitemaps


_FUNC_PAGE_RE = re.compile(
    r"/(login|signin|signup|register|cart|checkout|account|auth|contact)(/|$)", re.I
)
_NOISY_SITEMAP_RE = re.compile(r"/(search|tag|page/\d+|sessions?)($|/|\?)", re.I)
_FAQ_VISIBLE_RE = re.compile(r"(frequently asked|common questions|\bFAQ\b|^\s*Q[:：]|常见问题)", re.I | re.M)
_ARTICLE_TYPES = frozenset({"Article", "TechArticle", "NewsArticle", "BlogPosting"})


class DiagnosticLayerResult(BaseModel):
    key: str  # access | orient | understand | quote
    name: str
    question: str
    status: str  # ok | warn | fail | blocked
    score: Optional[float] = None
    blocked_by: Optional[str] = None
    issues: List[str] = Field(default_factory=list)


class DependencyChainReport(BaseModel):
    layers: List[DiagnosticLayerResult] = Field(default_factory=list)
    first_failing_layer: Optional[str] = None
    sitemap_noisy_urls: List[str] = Field(default_factory=list)
    duplicate_title_groups: int = 0
    near_duplicate_body_groups: int = 0
    schema_content_mismatches: List[str] = Field(default_factory=list)
    missing_article_authors: List[str] = Field(default_factory=list)
    spa_shell_urls: List[str] = Field(default_factory=list)


def _jsonld_has_key(obj: Any, keys: set[str]) -> bool:
    if isinstance(obj, dict):
        return any(k in keys or _jsonld_has_key(v, keys) for k, v in obj.items())
    if isinstance(obj, list):
        return any(_jsonld_has_key(x, keys) for x in obj)
    return False


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def evaluate_dependency_chain(
    *,
    pages: Sequence[Any],
    robots_txt: str = "",
    has_sitemap: bool = False,
    sitemap_urls: Sequence[str] = (),
    has_llms_txt: bool = False,
    llms_txt_check: Optional[Dict[str, Any]] = None,
    ai_ua_blocked: Sequence[str] = (),
    quotability_score: Optional[float] = None,
    pages_without_quotable_passage: int = 0,
) -> DependencyChainReport:
    """Compute the 4-layer GEO dependency chain with upstream-first blocker propagation."""
    n = max(len(pages), 1)
    sample_paths = [urlparse(str(_get(p, "url", ""))).path or "/" for p in pages[:12]]
    bots_blocked, bots_partial = check_ai_bots_robots(robots_txt, sample_paths=sample_paths) if robots_txt else ([], [])

    spa_shells: List[str] = []
    noindex_pages: List[str] = []
    unreachable_pages: List[str] = []
    no_canonical_pages = 0
    no_jsonld_pages = 0
    schema_mismatches: List[str] = []
    missing_authors: List[str] = []
    hreflang_pages = 0
    langs_seen: set[str] = set()
    by_title: Dict[str, List[str]] = {}
    by_body: Dict[str, List[str]] = {}

    for p in pages:
        url = str(_get(p, "url", "") or "")
        status = int(_get(p, "status_code", _get(p, "status", 200)) or 0)
        body = str(_get(p, "body_text", _get(p, "text", "")) or "")
        wc = int(_get(p, "word_count", len(body.split())) or 0)
        title = str(_get(p, "title", "") or "").strip()
        meta_robots = str(_get(p, "meta_robots", "") or "").lower()
        x_robots = str(_get(p, "x_robots_tag", "") or "").lower()
        canon = str(_get(p, "canonical_url", _get(p, "canonical", "")) or "")
        schema_types = set(_get(p, "schema_types", _get(p, "jsonld_types", [])) or [])
        json_ld = _get(p, "json_ld", _get(p, "jsonld_raw", [])) or []
        hreflang = _get(p, "hreflang", _get(p, "hreflangs", [])) or []
        lang = str(_get(p, "lang", _get(p, "language", "")) or "").strip().lower()

        if status != 200:
            unreachable_pages.append(url)
        if "noindex" in meta_robots or "noindex" in x_robots:
            noindex_pages.append(url)
        if status == 200 and wc < 120 and not _FUNC_PAGE_RE.search(urlparse(url).path):
            spa_shells.append(url)
        if not canon:
            no_canonical_pages += 1
        if not schema_types:
            no_jsonld_pages += 1
        if "FAQPage" in schema_types and not _FAQ_VISIBLE_RE.search(body):
            schema_mismatches.append(url)
        if (schema_types & _ARTICLE_TYPES) and not _jsonld_has_key(json_ld, {"author"}):
            missing_authors.append(url)
        if hreflang:
            hreflang_pages += 1
        if lang:
            langs_seen.add(lang.split("-")[0])

        if status == 200 and wc >= 120:
            if title:
                by_title.setdefault(title, []).append(url)
            body_key = hashlib.md5(re.sub(r"\s+", "", body[:600]).encode("utf-8")).hexdigest()
            by_body.setdefault(body_key, []).append(url)

    dup_titles = [us for us in by_title.values() if len(us) > 1]
    dup_bodies = [us for us in by_body.values() if len(us) > 1]
    noisy_sitemaps = [u for u in sitemap_urls if "?" in u or _NOISY_SITEMAP_RE.search(u)]
    robots_has_sitemap = bool(declared_sitemaps(robots_txt)) if robots_txt else False
    lch = llms_txt_check or {}

    def _build_layer(
        key: str,
        name: str,
        question: str,
        entries: List[Optional[tuple[str, str]]],
        raw_score: Optional[float] = None,
    ) -> DiagnosticLayerResult:
        clean = [e for e in entries if e]
        status = "fail" if any(s == "fail" for s, _ in clean) else ("warn" if clean else "ok")
        return DiagnosticLayerResult(
            key=key,
            name=name,
            question=question,
            status=status,
            score=raw_score,
            issues=[msg for _, msg in clean],
        )

    access = _build_layer(
        "access",
        "Access",
        "Can AI crawlers fetch static content?",
        [
            ("fail", f"robots.txt blocks AI crawlers sitewide: {', '.join(bots_blocked)}") if bots_blocked else None,
            ("fail", f"WAF/CDN differential block on AI UAs: {', '.join(ai_ua_blocked)}") if ai_ua_blocked else None,
            ("warn", f"robots.txt blocks partial content paths for {len(bots_partial)} AI bots") if bots_partial else None,
            (("fail" if len(spa_shells) >= n * 0.3 else "warn"), f"{len(spa_shells)} non-functional page(s) have empty static HTML (SPA shell)") if spa_shells else None,
            (("fail" if len(noindex_pages) >= n * 0.3 else "warn"), f"{len(noindex_pages)} page(s) carry meta or X-Robots-Tag noindex") if noindex_pages else None,
            ("warn", f"{len(unreachable_pages)} page(s) returned non-200 status") if unreachable_pages else None,
        ],
    )

    orient = _build_layer(
        "orient",
        "Orientation",
        "Can crawlers discover and disambiguate canonical URLs?",
        [
            ("fail", "No sitemap.xml discovered") if not has_sitemap else None,
            ("warn", "robots.txt does not declare a Sitemap: directive") if has_sitemap and robots_txt and not robots_has_sitemap else None,
            ("warn", "No /llms.txt official index found") if not has_llms_txt else None,
            ("warn", f"llms.txt has {len(lch.get('broken', []))} broken link(s)") if lch.get("broken") else None,
            ("warn", f"llms.txt links to {len(lch.get('robots_blocked', []))} path(s) blocked by robots.txt") if lch.get("robots_blocked") else None,
            ("warn", f"{no_canonical_pages} page(s) missing canonical tag") if no_canonical_pages else None,
            ("warn", f"sitemap contains {len(noisy_sitemaps)} noisy parameter/search/pagination URL(s)") if noisy_sitemaps else None,
            ("warn", f"{len(dup_titles)} duplicate <title> group(s) detected") if dup_titles else None,
            ("warn", f"{len(dup_bodies)} near-duplicate body group(s) detected") if dup_bodies else None,
            ("warn", f"Multilingual site has low hreflang coverage ({hreflang_pages}/{len(pages)} pages)") if len(langs_seen) >= 2 and hreflang_pages < len(pages) * 0.3 else None,
        ],
    )

    understand = _build_layer(
        "understand",
        "Understanding",
        "Can machines identify entities and verify schema against visible text?",
        [
            (("fail" if no_jsonld_pages >= n * 0.5 else "warn"), f"{no_jsonld_pages}/{len(pages)} page(s) have no JSON-LD structured data") if pages and no_jsonld_pages else None,
            ("warn", f"{len(schema_mismatches)} page(s) declare FAQPage JSON-LD without visible Q&A content (SCHEMA_CONTENT_MISMATCH)") if schema_mismatches else None,
            ("warn", f"{len(missing_authors)} article page(s) lack JSON-LD author entity (NO_AUTHOR_ENTITY)") if missing_authors else None,
        ],
    )

    quote_entries: List[Optional[tuple[str, str]]] = []
    if quotability_score is not None and quotability_score < 70.0:
        quote_entries.append(("fail" if quotability_score < 45.0 else "warn", f"Quotability score {quotability_score:.1f}/100 is below 70 readiness threshold"))
    if pages_without_quotable_passage > 0:
        quote_entries.append(("warn", f"{pages_without_quotable_passage} page(s) have zero independently quotable passages (NO_QUOTABLE_PASSAGE)"))
    quote = _build_layer(
        "quote",
        "Quotability",
        "Do pages contain self-contained, verifiable passages worth citing?",
        quote_entries,
        raw_score=quotability_score,
    )

    layers = [access, orient, understand, quote]
    first_fail: Optional[str] = None
    for layer in layers:
        if first_fail is not None:
            layer.blocked_by = first_fail
            layer.status = "blocked"
            layer.score = None  # Never emit misleading downstream scores when upstream fails
        elif layer.status == "fail":
            first_fail = layer.key

    return DependencyChainReport(
        layers=layers,
        first_failing_layer=first_fail,
        sitemap_noisy_urls=noisy_sitemaps[:20],
        duplicate_title_groups=len(dup_titles),
        near_duplicate_body_groups=len(dup_bodies),
        schema_content_mismatches=schema_mismatches[:20],
        missing_article_authors=missing_authors[:20],
        spa_shell_urls=spa_shells[:20],
    )
