"""
Dristik AI Sitemap Orphan Page Reporting Engine
Deterministic detection and reporting of orphan URLs found in sitemaps
that lack internal inbound links in the website crawl graph.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from app.domain.enums import Category, Severity
from app.domain.models import CrawlManifest, Finding, FindingEvidence
from app.evidence.models import EvidenceRef

logger = logging.getLogger("dristik.analyzers.sitemap_orphan")


def _compute_hash(data: Any) -> str:
    s = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class SitemapOrphanAnalyzer:
    """
    Analyzes crawl manifest orphan URLs to surface isolated pages
    that are declared in XML sitemaps but unreachable through site navigation.
    """

    def analyze(self, manifest: CrawlManifest) -> Dict[str, Any]:
        orphan_urls = manifest.orphan_urls or []
        sitemap_urls = manifest.sitemap_urls or []
        total_discovered = manifest.total_pages_discovered or len(manifest.pages or [])
        findings: List[Finding] = []

        orphan_count = len(orphan_urls)
        sitemap_count = len(sitemap_urls)
        orphan_ratio = (orphan_count / max(sitemap_count, 1)) if sitemap_count > 0 else 0.0

        if orphan_count > 0:
            sample_orphans = orphan_urls[:10]
            severity = Severity.HIGH if orphan_count > 5 or orphan_ratio > 0.15 else Severity.MEDIUM
            ev_hash = _compute_hash({"orphan_urls": orphan_urls, "sitemap_count": sitemap_count})
            ev_ref = EvidenceRef(
                source_type="crawl",
                source_id="sitemap_orphan_report",
                evidence_hash=ev_hash,
                url=sample_orphans[0] if sample_orphans else None,
                snippet=f"{orphan_count} orphan URLs in sitemap without internal links: {', '.join(sample_orphans[:3])}",
                metadata={
                    "orphan_count": orphan_count,
                    "sitemap_count": sitemap_count,
                    "orphan_ratio": round(orphan_ratio, 4),
                    "orphan_sample": sample_orphans,
                }
            )

            finding = Finding(
                finding_id=f"finding_sitemap_orphans_{ev_hash[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=severity,
                title=f"{orphan_count} Orphan Page(s) Found in XML Sitemap",
                description=(
                    f"Discovered {orphan_count} page(s) listed in XML sitemaps ({round(orphan_ratio * 100, 1)}% of sitemap) "
                    "that have zero inbound internal links from crawled site pages. "
                    f"Sample orphans: {', '.join(sample_orphans[:5])}"
                ),
                recommendation=(
                    "Integrate orphan pages into the website's navigational hierarchy (e.g. category pages, footer, or in-content links). "
                    "If these pages are deprecated or legacy landing pages, remove them from the XML sitemap."
                ),
                why_it_matters=(
                    "Orphan pages receive zero internal PageRank equity. Search engines may crawl them rarely or fail to rank them, "
                    "and users cannot discover them through natural browsing journeys."
                ),
                validation_criteria=(
                    "Every indexable URL in the XML sitemap must have at least one internal inbound HTML link from a crawled page."
                ),
                evidence=[
                    FindingEvidence(
                        url=u,
                        element="sitemap.xml",
                        value="Listed in sitemap with 0 internal inbound links",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )
                    for u in sample_orphans[:5]
                ],
                evidence_refs=[ev_ref.source_id],
                evidence_ref_objects=[ev_ref],
                impact=7 if severity == Severity.HIGH else 5,
                effort=3,
                priority=7 if severity == Severity.HIGH else 5,
            )
            findings.append(finding)

        # XML Sitemap Hygiene Checks against crawled pages
        crawled_pages = manifest.pages or []
        page_map = {p.url.rstrip("/"): p for p in crawled_pages if p.url}

        dirty_sitemap_urls = []
        for s_url in sitemap_urls:
            norm_s = s_url.rstrip("/")
            if norm_s in page_map:
                pe = page_map[norm_s]
                # Non-200
                if pe.status_code >= 300:
                    dirty_sitemap_urls.append({
                        "url": s_url,
                        "issue": f"Returns HTTP {pe.status_code}",
                        "status_code": pe.status_code
                    })
                # Noindex
                robots_str = f"{pe.robots_meta or ''} {pe.x_robots_tag or ''}".lower()
                if "noindex" in robots_str:
                    dirty_sitemap_urls.append({
                        "url": s_url,
                        "issue": "Declares 'noindex' directive",
                        "status_code": pe.status_code
                    })
                # Canonicalized to different URL
                if pe.canonical_url and pe.canonical_url.rstrip("/") != norm_s and pe.canonical_url.startswith("http"):
                    dirty_sitemap_urls.append({
                        "url": s_url,
                        "issue": f"Canonicalized to '{pe.canonical_url}'",
                        "status_code": pe.status_code
                    })

        if dirty_sitemap_urls:
            ev_hash_dirty = _compute_hash({"dirty_sitemap_urls": [d["url"] for d in dirty_sitemap_urls]})
            ev_ref_dirty = EvidenceRef(
                source_type="crawl",
                source_id="sitemap_hygiene_report",
                evidence_hash=ev_hash_dirty,
                url=dirty_sitemap_urls[0]["url"],
                snippet=f"{len(dirty_sitemap_urls)} non-indexable/redirecting URLs in XML sitemap",
                metadata={"dirty_count": len(dirty_sitemap_urls), "items": dirty_sitemap_urls[:10]}
            )
            findings.append(Finding(
                finding_id=f"finding_sitemap_hygiene_{ev_hash_dirty[:8]}",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=f"{len(dirty_sitemap_urls)} Non-Indexable or Redirecting URL(s) in XML Sitemap",
                description=(
                    f"Discovered {len(dirty_sitemap_urls)} URL(s) listed in the XML sitemap that return non-200 HTTP statuses, "
                    "declare 'noindex', or point to alternate canonical URLs. "
                    f"Sample: {', '.join(d['url'] for d in dirty_sitemap_urls[:3])}"
                ),
                recommendation=(
                    "Clean the XML sitemap so it strictly contains canonical, indexable HTTP 200 URLs. "
                    "Remove 3xx redirects, 404 client errors, and noindexed pages immediately."
                ),
                why_it_matters=(
                    "Google uses XML sitemaps to allocate crawl budget. Feeding search engines non-indexable or redirecting URLs "
                    "wastes crawl capacity and delays indexing of new commercial content."
                ),
                validation_criteria="Every URL listed in the XML sitemap must return HTTP 200, lack 'noindex', and be self-canonical.",
                evidence=[
                    FindingEvidence(
                        url=d["url"],
                        element="sitemap.xml",
                        value=d["issue"],
                        source="crawl",
                        evidence_ref=ev_ref_dirty,
                    )
                    for d in dirty_sitemap_urls[:5]
                ],
                evidence_refs=[ev_ref_dirty.source_id],
                evidence_ref_objects=[ev_ref_dirty],
                impact=7,
                effort=2,
                priority=7,
            ))

        summary = {
            "sitemap_urls_count": sitemap_count,
            "orphan_urls_count": orphan_count,
            "dirty_sitemap_urls_count": len(dirty_sitemap_urls),
            "orphan_ratio": round(orphan_ratio, 4),
            "findings_count": len(findings),
            "sample_orphans": orphan_urls[:10],
        }

        return {
            "summary": summary,
            "findings": findings,
        }
