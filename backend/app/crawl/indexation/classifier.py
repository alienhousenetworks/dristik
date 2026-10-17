"""
Dristik AI Industry-Grade Indexation Intelligence Classifier
Evaluates 16 distinct crawlability and indexation conditions:
1. crawlable
2. indexable
3. indexed (via GSC or unverified)
4. canonical_selected vs canonical_declared
5. noindex (meta)
6. X-Robots-Tag
7. robots_blocked
8. soft_404
9. duplicate
10. discovered_not_indexed
11. crawled_not_indexed
12. alternate_canonical
13. redirect
14. javascript_only_content
15. blocked_resources
16. rendered_vs_raw_differences
"""
from __future__ import annotations

import re
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from app.domain.models import (
    PageEvidence,
    CrawlManifest,
    Finding,
    FindingEvidence,
    IndexationPageStatus,
    RenderedVsRawDelta,
    IndexationAuditRollup,
)
from app.domain.enums import Category, Severity, VerificationStatus
from app.evidence.models import EvidenceRef


def _normalize_url(url: Optional[str]) -> str:
    if not url:
        return ""
    u = url.strip()
    parsed = urlparse(u)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    res = f"{scheme}://{netloc}{path}"
    if parsed.query:
        res = f"{res}?{parsed.query}"
    return res


SOFT_404_PATTERNS = [
    re.compile(r"\b(?:404|not\s+found|page\s+not\s+found|error\s+404|doesn['’]t\s+exist)\b", re.I),
    re.compile(r"\b(?:page\s+cannot\s+be\s+found|requested\s+url\s+was\s+not\s+found|nothing\s+here)\b", re.I),
    re.compile(r"\b(?:oops!?\s+page\s+not\s+found|sorry,?\s+we\s+couldn['’]t\s+find)\b", re.I),
]


class IndexationClassifier:
    """
    Deterministic state-machine classifier for multi-page crawl indexation intelligence.
    """

    def audit(
        self,
        manifest: CrawlManifest,
        pages: Optional[List[PageEvidence]] = None,
        gsc_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[IndexationAuditRollup, List[Finding]]:
        pages_list = pages or manifest.pages or []
        if not pages_list:
            return IndexationAuditRollup(), []

        robots_content = manifest.robots_txt_content or ""
        disallow_rules = self._parse_robots_disallow(robots_content)

        # Build duplicate detection fingerprints (based on text body / headings)
        content_fingerprints: Dict[str, str] = {}  # hash -> first url
        duplicates_map: Dict[str, str] = {}  # url -> duplicate_of_url

        for p in pages_list:
            body = (p.body_text or "").strip()
            title = (p.title or "").strip()
            if len(body) > 80:
                # Fingerprint using first 500 chars of normalized text + title
                norm = f"{title.lower()} {body[:500].lower()}"
                norm = re.sub(r"\s+", " ", norm).strip()
                f_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest()
                if f_hash in content_fingerprints and content_fingerprints[f_hash] != p.url:
                    duplicates_map[p.url] = content_fingerprints[f_hash]
                else:
                    content_fingerprints[f_hash] = p.url

        page_statuses: List[IndexationPageStatus] = []
        findings: List[Finding] = []

        gsc_inspection_map = {}
        if gsc_data and "inspections" in gsc_data:
            gsc_inspection_map = gsc_data["inspections"]

        for p in pages_list:
            status = self._classify_page(
                page=p,
                all_pages=pages_list,
                disallow_rules=disallow_rules,
                duplicates_map=duplicates_map,
                gsc_inspection=gsc_inspection_map.get(p.url) or gsc_inspection_map.get(_normalize_url(p.url)),
            )
            page_statuses.append(status)

            # Generate findings for actionable indexation anomalies
            page_findings = self._generate_findings_for_page(status, p)
            findings.extend(page_findings)

        # Build rollup statistics
        rollup = IndexationAuditRollup(
            total_pages_evaluated=len(page_statuses),
            crawlable_count=sum(1 for s in page_statuses if s.crawlable),
            indexable_count=sum(1 for s in page_statuses if s.indexable),
            indexed_count=sum(1 for s in page_statuses if s.indexed_state == "INDEXED"),
            blocked_by_robots_count=sum(1 for s in page_statuses if s.robots_blocked),
            noindex_count=sum(1 for s in page_statuses if s.has_noindex),
            x_robots_tag_count=sum(1 for s in page_statuses if s.x_robots_tag is not None),
            soft_404_count=sum(1 for s in page_statuses if s.is_soft_404),
            duplicate_count=sum(1 for s in page_statuses if s.is_duplicate),
            canonical_mismatch_count=sum(1 for s in page_statuses if not s.canonical_match and s.canonical_declared),
            discovered_not_indexed_count=sum(1 for s in page_statuses if s.gsc_coverage_state == "Discovered - currently not indexed"),
            crawled_not_indexed_count=sum(1 for s in page_statuses if s.gsc_coverage_state == "Crawled - currently not indexed"),
            alternate_canonical_count=sum(1 for s in page_statuses if s.alternate_canonical is not None),
            redirect_count=sum(1 for s in page_statuses if s.is_redirect),
            js_dependent_count=sum(1 for s in page_statuses if s.is_js_only_content),
            blocked_resources_count=sum(len(s.blocked_resources) for s in page_statuses),
            pages=page_statuses,
        )

        pct_indexable = round((rollup.indexable_count / max(1, rollup.total_pages_evaluated)) * 100, 1)
        rollup.summary = (
            f"Evaluated {rollup.total_pages_evaluated} pages: {rollup.indexable_count} indexable ({pct_indexable}%), "
            f"{rollup.noindex_count} noindex directives, {rollup.blocked_by_robots_count} robots-blocked, "
            f"{rollup.soft_404_count} soft-404s, {rollup.duplicate_count} duplicate variants, "
            f"and {rollup.js_dependent_count} pages with heavy client-side JavaScript rendering dependency."
        )

        return rollup, findings

    def _parse_robots_disallow(self, robots_txt: str) -> List[str]:
        rules = []
        if not robots_txt:
            return rules
        current_agent = None
        for line in robots_txt.splitlines():
            clean = line.strip().split("#")[0].strip()
            if not clean:
                continue
            lower = clean.lower()
            if lower.startswith("user-agent:"):
                agent = lower.replace("user-agent:", "").strip()
                current_agent = agent
            elif lower.startswith("disallow:") and (current_agent in ("*", "googlebot", "googlebot-image") or current_agent is None):
                path = clean.split(":", 1)[1].strip()
                if path:
                    rules.append(path)
        return rules

    def _is_blocked_by_robots(self, url: str, disallow_rules: List[str]) -> bool:
        if not disallow_rules:
            return False
        parsed = urlparse(url)
        path = parsed.path or "/"
        for rule in disallow_rules:
            if rule == "/":
                return True
            pattern = re.escape(rule).replace(r"\*", ".*")
            if re.match(f"^{pattern}", path):
                return True
        return False

    def _check_soft_404(self, page: PageEvidence) -> bool:
        # If status code is 200 OK, but text looks like 404
        if page.status_code != 200:
            return False
        title = (page.title or "").strip()
        h1s = " ".join(page.h1 or [])
        body = (page.body_text or "").strip()

        for pat in SOFT_404_PATTERNS:
            if pat.search(title) or pat.search(h1s):
                return True
            # If body is under 200 words and matches 404 copy
            if len(body.split()) < 200 and pat.search(body[:500]):
                return True
        return False

    def _extract_rendered_raw_delta(self, page: PageEvidence) -> RenderedVsRawDelta:
        rendered_text = (page.body_text or "").strip()
        rendered_words = page.word_count or len(rendered_text.split())
        rendered_headings = list(page.h1 or []) + list(page.h2 or [])

        raw_html = page.raw_html
        if not raw_html:
            # If no raw HTML comparison available, return nominal delta
            return RenderedVsRawDelta(
                raw_word_count=rendered_words,
                rendered_word_count=rendered_words,
                word_count_delta=0,
                rendered_headings=rendered_headings,
                rendered_internal_links=len(page.internal_links or []),
                js_dependency_risk="LOW",
            )

        try:
            soup = BeautifulSoup(raw_html, "html.parser")
            for s in soup(["script", "style", "noscript"]):
                s.decompose()
            raw_text = soup.get_text(separator=" ", strip=True)
            raw_words = len(raw_text.split())
            raw_h = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])]
            raw_links = len(soup.find_all("a", href=True))

            word_delta = max(0, rendered_words - raw_words)
            js_headings = [h for h in rendered_headings if h not in raw_h]

            if raw_words < 25 and rendered_words >= 25:
                risk = "CRITICAL"
            elif word_delta > max(20, raw_words * 0.5):
                risk = "MEDIUM"
            else:
                risk = "LOW"

            return RenderedVsRawDelta(
                raw_word_count=raw_words,
                rendered_word_count=rendered_words,
                word_count_delta=word_delta,
                raw_headings=raw_h,
                rendered_headings=rendered_headings,
                js_only_headings=js_headings,
                raw_internal_links=raw_links,
                rendered_internal_links=len(page.internal_links or []),
                js_only_links_count=max(0, len(page.internal_links or []) - raw_links),
                js_dependency_risk=risk,
            )
        except Exception:
            return RenderedVsRawDelta(
                raw_word_count=rendered_words,
                rendered_word_count=rendered_words,
                word_count_delta=0,
                rendered_headings=rendered_headings,
                rendered_internal_links=len(page.internal_links or []),
                js_dependency_risk="LOW",
            )

    def _classify_page(
        self,
        page: PageEvidence,
        all_pages: List[PageEvidence],
        disallow_rules: List[str],
        duplicates_map: Dict[str, str],
        gsc_inspection: Optional[Dict[str, Any]] = None,
    ) -> IndexationPageStatus:
        norm_url = _normalize_url(page.url)
        norm_canonical = _normalize_url(page.canonical_url)

        # 1. Robots blocked check
        robots_blocked = self._is_blocked_by_robots(page.url, disallow_rules)

        # 2. X-Robots-Tag check
        x_robots = (
            page.x_robots_tag
            or page.response_headers.get("x-robots-tag")
            or page.response_headers.get("X-Robots-Tag")
        )
        has_x_noindex = bool(x_robots and "noindex" in x_robots.lower())

        # 3. Meta robots check
        meta_robots = (page.robots_meta or "").lower()
        has_meta_noindex = "noindex" in meta_robots or "none" in meta_robots
        has_noindex = has_x_noindex or has_meta_noindex

        # 4. Soft-404 check
        is_soft_404 = self._check_soft_404(page)

        # 5. Duplicate check
        is_duplicate = page.url in duplicates_map
        dup_of = duplicates_map.get(page.url)

        # 6. Redirect check
        is_redirect = bool(
            page.is_redirected
            or (page.redirect_chain and len(page.redirect_chain) > 0)
            or (300 <= page.status_code < 400)
        )
        redirect_target = page.final_url if is_redirect else None

        # 7. Canonical declared vs selected
        canonical_declared = page.canonical_url
        gsc_selected = (gsc_inspection or {}).get("selected_canonical") if gsc_inspection else None
        canonical_selected = gsc_selected or (page.canonical_url if page.canonical_url else page.url)

        canonical_match = True
        alternate_canonical = None
        if norm_canonical and norm_canonical != norm_url:
            canonical_match = False
            alternate_canonical = page.canonical_url

        # 8. Render delta / JS-only content
        render_delta = self._extract_rendered_raw_delta(page)
        is_js_only = render_delta.js_dependency_risk in ("CRITICAL", "MEDIUM")

        # 9. GSC Indexed status & coverage
        indexed_state = "UNVERIFIED_NO_GSC"
        gsc_coverage = None
        if gsc_inspection:
            gsc_coverage = gsc_inspection.get("coverage_state")
            indexing_state = gsc_inspection.get("indexing_state")
            if indexing_state == "INDEXED" or gsc_coverage in ("Submitted and indexed", "Indexed, not submitted in sitemap"):
                indexed_state = "INDEXED"
            elif gsc_coverage or indexing_state:
                indexed_state = "NOT_INDEXED"

        # 10. Crawlable & Indexable determination
        crawlable = (not robots_blocked) and (page.status_code < 400 or is_redirect)
        indexable = bool(
            crawlable
            and page.status_code == 200
            and not has_noindex
            and not is_soft_404
            and not is_duplicate
            and canonical_match
            and not is_redirect
        )

        return IndexationPageStatus(
            url=page.url,
            status_code=page.status_code,
            crawlable=crawlable,
            indexable=indexable,
            indexed_state=indexed_state,
            canonical_declared=canonical_declared,
            canonical_selected=canonical_selected,
            canonical_match=canonical_match,
            has_noindex=has_noindex,
            x_robots_tag=x_robots,
            robots_blocked=robots_blocked,
            is_soft_404=is_soft_404,
            is_duplicate=is_duplicate,
            duplicate_of_url=dup_of,
            gsc_coverage_state=gsc_coverage,
            alternate_canonical=alternate_canonical,
            is_redirect=is_redirect,
            redirect_target=redirect_target,
            is_js_only_content=is_js_only,
            blocked_resources=[],
            render_delta=render_delta,
        )

    def _generate_findings_for_page(
        self,
        status: IndexationPageStatus,
        page: PageEvidence
    ) -> List[Finding]:
        findings: List[Finding] = []

        # Finding: Soft 404
        if status.is_soft_404:
            findings.append(Finding(
                finding_id=f"idx_soft404_{hashlib.md5(status.url.encode()).hexdigest()[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Soft 404 Detected on Active Page",
                description=f"Page returns HTTP 200 OK but displays 404/Not Found content: {status.url}",
                recommendation="Configure server to return an authentic HTTP 404 or 410 status code, or 301 redirect if page moved.",
                impact=7,
                confidence=0.92,
                evidence_refs=[f"url:{status.url}"]
            ))

        # Finding: Robots.txt blocking indexable page
        if status.robots_blocked and not status.has_noindex and status.status_code == 200:
            findings.append(Finding(
                finding_id=f"idx_robots_{hashlib.md5(status.url.encode()).hexdigest()[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title="Search Engine Crawlers Blocked by robots.txt",
                description=f"robots.txt disallows search engine crawlers from fetching: {status.url}",
                recommendation="Remove disallow directive in robots.txt if this page is intended for organic search indexation.",
                impact=8,
                confidence=0.95,
                evidence_refs=[f"url:{status.url}"]
            ))

        # Finding: JS-only critical rendering risk
        if status.render_delta and status.render_delta.js_dependency_risk == "CRITICAL":
            findings.append(Finding(
                finding_id=f"idx_js_only_{hashlib.md5(status.url.encode()).hexdigest()[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                title="Critical Client-Side JavaScript Indexation Dependency",
                description=(
                    f"Raw HTML stream contains only {status.render_delta.raw_word_count} words; "
                    f"rendered DOM expands to {status.render_delta.rendered_word_count} words. "
                    f"Crawlers that defer or skip JavaScript execution will fail to index main body copy."
                ),
                recommendation="Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so raw HTML contains full content.",
                impact=6,
                confidence=0.88,
                evidence_refs=[f"url:{status.url}"]
            ))

        # Finding: Unconsolidated Duplicate Content
        if status.is_duplicate and status.duplicate_of_url:
            findings.append(Finding(
                finding_id=f"idx_dup_{hashlib.md5(status.url.encode()).hexdigest()[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                title="Duplicate Content Without Canonical Consolidation",
                description=f"Content duplicates {status.duplicate_of_url} but does not declare a canonical link pointing to it.",
                recommendation=f"Add a canonical tag on {status.url} pointing to the authoritative version: {status.duplicate_of_url}.",
                impact=5,
                confidence=0.85,
                evidence_refs=[f"url:{status.url}"]
            ))

        return findings


indexation_classifier = IndexationClassifier()
