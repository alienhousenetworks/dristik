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

        summary = {
            "sitemap_urls_count": sitemap_count,
            "orphan_urls_count": orphan_count,
            "orphan_ratio": round(orphan_ratio, 4),
            "findings_count": len(findings),
            "sample_orphans": orphan_urls[:10],
        }

        return {
            "summary": summary,
            "findings": findings,
        }
