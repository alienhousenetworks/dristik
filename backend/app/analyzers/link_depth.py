"""
Dristik AI Click-Depth Histogram, Orphan Page Detector & Anchor Equity Analyzer
1. Shortest-path click depth from homepage across internal link graph (Depth 1, 2, 3, 4+)
2. Orphan Page Inventory: cross-references sitemap URLs vs inlink counts (0 inlinks = orphan)
3. Anchor text audit: flags generic, low-equity anchor phrases ("click here", "read more", raw URLs)
"""
from typing import List, Dict, Set, Optional, Tuple
from collections import deque, defaultdict
from urllib.parse import urlparse
from app.domain.models import PageEvidence, ClickDepthReport, OrphanPageReport, AnchorTextAudit


_GENERIC_ANCHOR_PATTERNS = [
    "click here", "click this", "here", "read more", "learn more",
    "more info", "see more", "continue reading", "link", "website",
    "page", "this link", "view more", "details"
]


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    return clean or url


class LinkDepthAnalyzer:
    @staticmethod
    def analyze_click_depth(
        pages: List[PageEvidence],
        homepage_url: Optional[str] = None
    ) -> ClickDepthReport:
        if not pages:
            return ClickDepthReport(
                homepage_url=homepage_url or "",
                total_pages_analyzed=0
            )

        # Identify homepage
        if not homepage_url:
            homepage_candidate = pages[0].url
            for p in pages:
                path = urlparse(p.url).path.strip("/")
                if path in ("", "index.html", "index.php"):
                    homepage_candidate = p.url
                    break
            homepage_url = homepage_candidate

        clean_home = _normalize_url(homepage_url)

        # Build internal graph: source_url -> set(target_urls)
        graph: Dict[str, Set[str]] = defaultdict(set)
        inlink_counts: Dict[str, int] = defaultdict(int)
        all_crawled = set()

        for p in pages:
            src = _normalize_url(p.url)
            all_crawled.add(src)
            p.outlinks_internal_count = len(p.internal_links or [])
            p.outlinks_external_count = len(p.external_links or [])
            for link in (p.internal_links or []):
                tgt = _normalize_url(link)
                if tgt and tgt != src:
                    graph[src].add(tgt)
                    inlink_counts[tgt] += 1

        # Populate inlinks_count on PageEvidence objects
        for p in pages:
            src = _normalize_url(p.url)
            p.inlinks_count = inlink_counts.get(src, 0)

        # BFS shortest-path from homepage
        depths: Dict[str, int] = {}
        queue = deque([(clean_home, 0)])
        visited = {clean_home}

        while queue:
            curr, d = queue.popleft()
            depths[curr] = d
            for nxt in graph.get(curr, []):
                if nxt not in visited and nxt in all_crawled:
                    visited.add(nxt)
                    queue.append((nxt, d + 1))

        # Assign remaining unvisited crawled pages as Depth 4+ (disconnected or deep)
        for u in all_crawled:
            if u not in depths:
                depths[u] = 4

        # Group pages by depth bucket
        d1, d2, d3, d4_plus = [], [], [], []
        pages_by_depth: Dict[str, List[str]] = {
            "depth_1": [],
            "depth_2": [],
            "depth_3": [],
            "depth_4_plus": [],
        }

        for u, d in depths.items():
            if d == 1:
                d1.append(u)
                pages_by_depth["depth_1"].append(u)
            elif d == 2:
                d2.append(u)
                pages_by_depth["depth_2"].append(u)
            elif d == 3:
                d3.append(u)
                pages_by_depth["depth_3"].append(u)
            elif d >= 4:
                d4_plus.append(u)
                pages_by_depth["depth_4_plus"].append(u)
            elif d == 0:
                # Homepage counts at depth 1 as direct entry
                d1.append(u)
                pages_by_depth["depth_1"].append(u)

        total = max(1, len(depths))
        dist_pct = {
            "depth_1": round((len(d1) / total) * 100, 1),
            "depth_2": round((len(d2) / total) * 100, 1),
            "depth_3": round((len(d3) / total) * 100, 1),
            "depth_4_plus": round((len(d4_plus) / total) * 100, 1),
        }
        max_d = max(depths.values()) if depths else 0

        return ClickDepthReport(
            homepage_url=clean_home,
            total_pages_analyzed=len(depths),
            depth_1_count=len(d1),
            depth_2_count=len(d2),
            depth_3_count=len(d3),
            depth_4_plus_count=len(d4_plus),
            max_click_depth=max_d,
            pages_by_depth=pages_by_depth,
            depth_distribution_pct=dist_pct,
            high_depth_warning_count=len(d4_plus)
        )

    @staticmethod
    def detect_orphans(
        pages: List[PageEvidence],
        sitemap_urls: List[str],
        homepage_url: Optional[str] = None
    ) -> OrphanPageReport:
        if not sitemap_urls:
            return OrphanPageReport(
                total_sitemap_urls=0,
                total_crawled_urls=len(pages),
                orphan_urls=[],
                orphan_count=0,
                orphan_percentage=0.0,
                summary=(
                    f"Orphan page detection unmeasured: No XML sitemap was provided or discovered "
                    f"to cross-reference against the {len(pages)}-page crawl sample. Comprehensive orphan analysis "
                    f"requires sitemap.xml or Google Search Console index export."
                )
            )

        clean_home = _normalize_url(homepage_url or (pages[0].url if pages else ""))

        # Calculate inlink counts across internal pages
        inlinks: Dict[str, int] = defaultdict(int)
        for p in pages:
            src = _normalize_url(p.url)
            for link in (p.internal_links or []):
                tgt = _normalize_url(link)
                if tgt and tgt != src:
                    inlinks[tgt] += 1

        orphan_urls = []
        for s_url in sitemap_urls:
            clean_s = _normalize_url(s_url)
            if clean_s != clean_home and inlinks.get(clean_s, 0) == 0:
                orphan_urls.append(s_url)

        total_sitemap = len(sitemap_urls)
        orphan_count = len(orphan_urls)
        orphan_pct = round((orphan_count / max(1, total_sitemap)) * 100, 1)

        summary = (
            f"Found {orphan_count} orphan URL(s) in sitemap ({orphan_pct}% of {total_sitemap} total sitemap URLs) "
            f"with zero internal inlinks discovered during crawl."
        ) if orphan_count > 0 else (
            f"Zero orphan pages detected within the sample: all {total_sitemap} sitemap URLs receive internal links in the {len(pages)}-page crawl sample."
        )

        return OrphanPageReport(
            total_sitemap_urls=total_sitemap,
            total_crawled_urls=len(pages),
            orphan_urls=orphan_urls,
            orphan_count=orphan_count,
            orphan_percentage=orphan_pct,
            summary=summary
        )

    @staticmethod
    def audit_anchor_texts(pages: List[PageEvidence]) -> AnchorTextAudit:
        """Flags low-equity generic anchor text ('click here', 'read more', raw URLs)."""
        generic_hits: List[Dict[str, str]] = []
        term_counts: Dict[str, int] = defaultdict(int)
        total_links = 0

        for p in pages:
            links = (p.internal_links or []) + (p.external_links or [])
            total_links += len(links)

            # Check CTAs and body text for generic anchor patterns
            for cta in (p.ctas or []):
                cta_clean = cta.strip().lower()
                for gen in _GENERIC_ANCHOR_PATTERNS:
                    if gen == cta_clean or cta_clean.startswith(gen):
                        generic_hits.append({
                            "url": p.url,
                            "anchor": cta,
                            "reason": f"Generic low-equity anchor matches '{gen}'"
                        })
                        term_counts[gen] += 1
                        break

            # Check for raw URL anchors in CTAs
            for cta in (p.ctas or []):
                if cta.startswith("http://") or cta.startswith("https://") or cta.startswith("www."):
                    generic_hits.append({
                        "url": p.url,
                        "anchor": cta,
                        "reason": "Raw URL used as anchor text (naked link)"
                    })
                    term_counts["raw_url"] += 1

        terms_summary = [{"term": t, "count": c} for t, c in sorted(term_counts.items(), key=lambda x: -x[1])]
        summary = (
            f"Identified {len(generic_hits)} low-equity generic anchor text instances across {len(pages)} pages. "
            f"Replace phrases like 'click here' and raw URLs with descriptive keyword anchors."
        )

        return AnchorTextAudit(
            total_links_analyzed=total_links,
            generic_anchor_count=len(generic_hits),
            low_equity_terms_found=terms_summary,
            flagged_anchor_instances=generic_hits,
            summary=summary
        )


def analyze_link_depth_and_orphans(
    pages: List[PageEvidence],
    sitemap_urls: Optional[List[str]] = None,
    homepage_url: Optional[str] = None
) -> Tuple[ClickDepthReport, OrphanPageReport, AnchorTextAudit]:
    cd = LinkDepthAnalyzer.analyze_click_depth(pages, homepage_url)
    orphans = LinkDepthAnalyzer.detect_orphans(pages, sitemap_urls or [], homepage_url)
    anchors = LinkDepthAnalyzer.audit_anchor_texts(pages)
    return cd, orphans, anchors
