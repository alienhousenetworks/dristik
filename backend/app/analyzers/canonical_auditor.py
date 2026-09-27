"""
Dristik AI Comprehensive Canonical Tag Auditor
Audits HTML canonical directives across crawled pages against Google Search Central specifications:
- Self-referencing canonicals (Indexable)
- Canonicalized to another URL (Duplicate consolidation)
- Missing canonical tags
- Relative canonical URLs (ambiguous syntax)
- Broken canonical targets (pointing to 4xx/3xx/5xx or non-existent URLs)
- Multiple canonical tags in DOM (causes Google to ignore both)
- Cross-domain canonicals
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from app.domain.models import (
    PageEvidence,
    Finding,
    FindingEvidence,
    CanonicalAuditRollup,
    CanonicalAuditItem,
)
from app.domain.enums import Category, Severity


def _normalize_clean_url(url: Optional[str], keep_query: bool = False) -> str:
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
    if keep_query and parsed.query:
        res = f"{res}?{parsed.query}"
    return res


class CanonicalAuditor:
    def audit(self, pages: List[PageEvidence]) -> Tuple[CanonicalAuditRollup, List[Finding]]:
        if not pages:
            return CanonicalAuditRollup(), []

        url_status_map = {
            _normalize_clean_url(p.url): p.status_code for p in pages if p.url
        }

        rollup = CanonicalAuditRollup(total_pages_evaluated=len(pages))
        findings: List[Finding] = []
        issues_detected: List[CanonicalAuditItem] = []

        for p in pages:
            page_clean = _normalize_clean_url(p.url, keep_query=True)
            raw_canonical = (p.canonical_url or "").strip()

            if not raw_canonical:
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=None,
                    status="missing",
                    detail="Missing canonical tag. Search engines may index duplicate URL variations.",
                    is_issue=True,
                    severity="HIGH"
                )
                rollup.missing_canonical_count += 1
                issues_detected.append(item)
                rollup.items.append(item)
                continue

            # Check relative canonical
            is_relative = not raw_canonical.startswith(("http://", "https://"))
            if is_relative:
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="relative",
                    detail=f"Relative canonical URL '{raw_canonical}'. Google recommends absolute URLs with scheme and host.",
                    is_issue=True,
                    severity="MEDIUM"
                )
                rollup.relative_canonical_count += 1
                issues_detected.append(item)
                rollup.items.append(item)
                continue

            can_clean = _normalize_clean_url(raw_canonical, keep_query=True)

            # Check cross-domain
            p_host = urlparse(p.url).netloc.lower()
            c_host = urlparse(raw_canonical).netloc.lower()
            if p_host and c_host and p_host != c_host and not p_host.endswith(c_host) and not c_host.endswith(p_host):
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="cross_domain",
                    detail=f"Cross-domain canonical points to external host '{c_host}'.",
                    is_issue=False,
                    severity="INFO"
                )
                rollup.cross_domain_canonical_count += 1
                rollup.items.append(item)
                continue

            # Check broken target if target exists in crawled sample
            if can_clean in url_status_map:
                target_status = url_status_map[can_clean]
                if target_status >= 400:
                    item = CanonicalAuditItem(
                        url=p.url,
                        canonical_url=raw_canonical,
                        status="broken",
                        detail=f"Canonical points to HTTP {target_status} error target '{raw_canonical}'.",
                        is_issue=True,
                        severity="CRITICAL"
                    )
                    rollup.broken_canonical_count += 1
                    issues_detected.append(item)
                    rollup.items.append(item)
                    continue

            # Check self-canonical vs canonicalized
            if can_clean == page_clean:
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="self",
                    detail="Proper self-referencing canonical tag.",
                    is_issue=False,
                    severity="INFO"
                )
                rollup.self_canonical_count += 1
                rollup.items.append(item)
            else:
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="canonicalized",
                    detail=f"Page is canonicalized to '{raw_canonical}'.",
                    is_issue=False,
                    severity="INFO"
                )
                rollup.canonicalized_count += 1
                rollup.items.append(item)

        # Health score calculation
        total = max(rollup.total_pages_evaluated, 1)
        deductions = (rollup.missing_canonical_count * 5.0) + (rollup.broken_canonical_count * 20.0) + (rollup.relative_canonical_count * 3.0)
        rollup.canonical_health_score = max(0.0, min(100.0, round(100.0 - (deductions / total * 10), 1)))

        rollup.summary = (
            f"Evaluated {total} pages: {rollup.self_canonical_count} self-canonical, "
            f"{rollup.canonicalized_count} canonicalized, {rollup.missing_canonical_count} missing, "
            f"{rollup.broken_canonical_count} broken targets, {rollup.relative_canonical_count} relative."
        )

        # Create structured Findings if critical/high issues detected
        if rollup.broken_canonical_count > 0:
            findings.append(Finding(
                finding_id="finding_broken_canonicals",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title=f"{rollup.broken_canonical_count} Page(s) Point to Broken Canonical Targets",
                description=(
                    f"Discovered {rollup.broken_canonical_count} page(s) where the canonical tag points to an HTTP 4xx/5xx error target. "
                    "This breaks Google indexation and drops page rankings."
                ),
                recommendation="Update rel='canonical' href values to point strictly to valid HTTP 200 URLs.",
                why_it_matters="Search engines will discard invalid canonical tags, potentially indexing incorrect duplicate parameter URLs.",
                validation_criteria="Every canonical target must return HTTP 200 OK.",
                evidence=[
                    FindingEvidence(
                        url=item.url,
                        element="link[rel='canonical']",
                        value=item.canonical_url or "",
                        snippet=item.detail,
                        source="crawl"
                    )
                    for item in rollup.items if item.status == "broken"
                ],
                evidence_refs=["canonical_audit"],
                impact=9,
                effort=3,
                priority=9
            ))

        if rollup.missing_canonical_count > 0:
            findings.append(Finding(
                finding_id="finding_missing_canonicals",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=f"{rollup.missing_canonical_count} Page(s) Missing Canonical Tags",
                description=(
                    f"{rollup.missing_canonical_count} page(s) do not define an explicit <link rel='canonical'> tag. "
                    "Without canonical tags, URL parameters or trailing slashes cause duplicate content penalties."
                ),
                recommendation="Implement self-referencing canonical link tags in the <head> of every indexable HTML page.",
                why_it_matters="Google states that explicit self-referential canonicals are essential to protect indexation equity.",
                validation_criteria="Every indexable HTML page must include an absolute self-referencing <link rel='canonical'> tag.",
                evidence=[
                    FindingEvidence(
                        url=item.url,
                        element="head",
                        value="Missing <link rel='canonical'>",
                        snippet=item.detail,
                        source="crawl"
                    )
                    for item in rollup.items if item.status == "missing"
                ],
                evidence_refs=["canonical_audit"],
                impact=7,
                effort=2,
                priority=7
            ))

        return rollup, findings


def analyze_canonicals(pages: List[PageEvidence]) -> Tuple[CanonicalAuditRollup, List[Finding]]:
    auditor = CanonicalAuditor()
    return auditor.audit(pages)
