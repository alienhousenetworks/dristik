"""
Dristik AI Page-Level Analysis Engine (2026 Master Standard).

Compiles granular, page-by-page technical, on-page, structured data,
and performance dossiers for every evaluated URL across the audit crawl.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.domain.models import (
    CrawlManifest,
    ExecutiveReport,
    Finding,
    PageEvidence,
    PageLevelAssessment,
)

logger = logging.getLogger("dristik.audit.page_analysis")


class PageLevelAnalysisEngine:
    """
    Compiles deep, page-specific audits for every URL in the audit inventory.
    """

    @classmethod
    def compile_page_assessments(
        cls,
        pages: List[PageEvidence],
        report: ExecutiveReport,
        manifest: Optional[CrawlManifest] = None,
    ) -> List[PageLevelAssessment]:
        manifest = manifest or getattr(report, "crawl_manifest", None)
        findings = report.findings or []

        # Build URL to findings index
        url_findings_map: Dict[str, List[Finding]] = {}
        for f in findings:
            for u in f.affected_urls:
                norm_u = u.strip()
                if norm_u not in url_findings_map:
                    url_findings_map[norm_u] = []
                url_findings_map[norm_u].append(f)

        # Build depth index
        depth_map: Dict[str, int] = {}
        if report.click_depth and getattr(report.click_depth, "pages_by_depth", None):
            for depth_str, u_list in report.click_depth.pages_by_depth.items():
                try:
                    d_int = int(depth_str.replace("+", ""))
                    for u in u_list:
                        depth_map[u.strip()] = d_int
                except ValueError:
                    pass

        assessments: List[PageLevelAssessment] = []

        for p in pages:
            url = p.url or ""
            if not url:
                continue

            parsed = urlparse(url)
            path = parsed.path.lower().rstrip("/")

            # Determine page purpose
            if path in ("", "/"):
                purpose = "Primary Homepage & Brand Anchor"
            elif any(k in path for k in ("/product", "/service", "/solution", "/feature")):
                purpose = "Commercial Solution / Product Landing Page"
            elif any(k in path for k in ("/pricing", "/plan", "/tier")):
                purpose = "High-Intent Commercial Pricing Page"
            elif any(k in path for k in ("/contact", "/about", "/location")):
                purpose = "Brand Entity & Trust Authority Page"
            elif any(k in path for k in ("/blog", "/article", "/guide", "/resource", "/doc")):
                purpose = "Informational Authority & Discovery Guide"
            else:
                purpose = "Standard Content Landing Page"

            # Title & Meta length calculations
            title_str = p.title or ""
            title_len = len(title_str)
            title_px = int(title_len * 9.2)  # Typical Arial 20px letter width
            title_trunc = title_px > 580

            desc_str = p.meta_description or ""
            desc_len = len(desc_str)
            desc_trunc = desc_len > 160 or (desc_len * 5.8 > 960)

            # Headings outline
            outline: List[str] = []
            if getattr(p, "h2_list", None):
                outline.extend([str(h)[:60] for h in p.h2_list[:5]])

            # Indexability evaluation
            has_noindex = bool(getattr(p, "has_noindex", False))
            robots_blocked = bool(getattr(p, "robots_blocked", False))
            status_code = getattr(p, "status_code", 200) or 200
            is_indexable = (status_code == 200) and not has_noindex and not robots_blocked

            if not is_indexable:
                reasons = []
                if status_code != 200:
                    reasons.append(f"HTTP {status_code}")
                if has_noindex:
                    reasons.append("noindex directive present")
                if robots_blocked:
                    reasons.append("blocked by robots.txt")
                index_evidence = f"Non-indexable: {', '.join(reasons)}"
            else:
                index_evidence = "200 OK, indexable, noindex absent, allowed by robots.txt"

            # Canonical alignment
            can_url = p.canonical_url or ""
            canonical_match = True
            if can_url:
                norm_can = can_url.strip().rstrip("/")
                norm_self = url.strip().rstrip("/")
                canonical_match = (norm_can == norm_self)

            # Word count & quality
            wc = getattr(p, "word_count", 0) or 0
            if wc < 150:
                content_quality = "THIN_CONTENT"
            elif wc > 800:
                content_quality = "ROBUST_AUTHORITY"
            else:
                content_quality = "STANDARD"

            # Search intent
            if any(k in path for k in ("/pricing", "/checkout", "/buy", "/signup")):
                intent = "TRANSACTIONAL"
            elif any(k in path for k in ("/product", "/service", "/solution", "/vs-")):
                intent = "COMMERCIAL"
            elif any(k in path for k in ("/about", "/contact", "/login")):
                intent = "NAVIGATIONAL"
            else:
                intent = "INFORMATIONAL"

            # Find matching findings
            matched_findings = url_findings_map.get(url.strip(), [])
            issue_titles = [f.title for f in matched_findings]
            recommendations = [f.recommendation for f in matched_findings if f.recommendation]

            # Inlinks & Outlinks
            outlinks = len(getattr(p, "internal_links", []))
            inlinks = getattr(p, "inlinks_count", 0) or 0

            # Schema evaluation
            schema_types = list(getattr(p, "schema_types", []))
            has_schema = len(schema_types) > 0
            rich_eligible = has_schema and any(t in ["Organization", "Product", "Article", "FAQPage", "LocalBusiness", "BreadcrumbList"] for t in schema_types)

            # H1 handling (list or string)
            raw_h1 = getattr(p, "h1", None)
            if isinstance(raw_h1, list):
                h1_str = str(raw_h1[0]) if len(raw_h1) > 0 else None
                h1_cnt = len(raw_h1)
            elif raw_h1:
                h1_str = str(raw_h1)
                h1_cnt = 1
            else:
                h1_str = None
                h1_cnt = 0

            assessments.append(PageLevelAssessment(
                url=url,
                page_purpose=purpose,
                page_type=getattr(p, "page_type", "general") or "general",
                http_status=status_code,
                redirect_target=getattr(p, "redirect_target", None),
                ttfb_ms=float(getattr(p, "ttfb_ms", 0.0) or 0.0),
                indexable=is_indexable,
                indexability_evidence=index_evidence,
                canonical_declared=can_url if can_url else None,
                canonical_match=canonical_match,
                title=title_str if title_str else None,
                title_length=title_len,
                title_pixel_width=title_px,
                title_truncated=title_trunc,
                meta_description=desc_str if desc_str else None,
                meta_description_length=desc_len,
                meta_description_truncated=desc_trunc,
                h1=h1_str,
                h1_count=h1_cnt,
                heading_outline=outline,
                word_count=wc,
                main_content_quality=content_quality,
                search_intent=intent,
                intent_notes=f"Target intent: {intent}. Content volume: {wc} words.",
                internal_inlinks_count=inlinks,
                internal_outlinks_count=outlinks,
                click_depth=depth_map.get(url.strip(), 1),
                schema_types=schema_types,
                schema_valid=has_schema,
                rich_result_eligible=rich_eligible,
                mobile_viewport_ok=bool(getattr(p, "viewport", True)),
                open_issues_count=len(matched_findings),
                findings=issue_titles,
                recommended_changes=recommendations[:3],
            ))

        return assessments
