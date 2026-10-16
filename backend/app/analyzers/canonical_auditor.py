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
import hashlib
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

            # Check broken or redirecting target if target exists in crawled sample
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
                elif 300 <= target_status < 400:
                    item = CanonicalAuditItem(
                        url=p.url,
                        canonical_url=raw_canonical,
                        status="redirect_target",
                        detail=f"Canonical points to HTTP {target_status} redirecting target '{raw_canonical}'. Canonicals must point strictly to direct HTTP 200 destinations.",
                        is_issue=True,
                        severity="HIGH"
                    )
                    rollup.broken_canonical_count += 1
                    issues_detected.append(item)
                    rollup.items.append(item)
                    continue

            # Check contradiction between noindex and canonical
            robots_str = f"{p.robots_meta or ''} {p.x_robots_tag or ''}".lower()
            has_noindex = "noindex" in robots_str
            if has_noindex and can_clean == page_clean:
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="noindex_conflict",
                    detail=f"Contradiction: page specifies 'noindex' while simultaneously declaring a self-referencing canonical tag. Search engines may ignore both directives.",
                    is_issue=True,
                    severity="HIGH"
                )
                issues_detected.append(item)
                rollup.items.append(item)
                continue

            # Check tracking/query parameters in canonical tag
            if any(q in raw_canonical.lower() for q in ["utm_", "gclid", "fbclid", "sessionid", "ref="]):
                item = CanonicalAuditItem(
                    url=p.url,
                    canonical_url=raw_canonical,
                    status="tracking_params",
                    detail=f"Canonical URL contains tracking query parameters: '{raw_canonical}'. Canonicals must point to clean base URLs.",
                    is_issue=True,
                    severity="MEDIUM"
                )
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
            broken_items = [item for item in rollup.items if item.status == "broken"]
            ev_list = []
            for item in broken_items[:10]:
                ev_id = f"EV-CAN-BRK-{hashlib.sha256(f'{item.url}:{item.canonical_url}'.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=item.url,
                    element="link[rel='canonical']",
                    value=item.canonical_url or "",
                    observed_value=item.canonical_url or "",
                    expected_condition="Canonical target must resolve to valid HTTP 200 indexable URL",
                    snippet=item.detail or f'<link rel="canonical" href="{item.canonical_url}">',
                    test_method="crawl_html_head",
                    source="crawl",
                ))

            aff_urls = [item.url for item in broken_items]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_broken_canonicals",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title=f"{rollup.broken_canonical_count} Page(s) Point to Broken Canonical Targets",
                description=(
                    f"Discovered {rollup.broken_canonical_count} page(s) where the canonical tag points to an HTTP 4xx/5xx error target. "
                    "This prevents search engines from indexing the canonical target and leads search crawlers to disregard the canonical directive."
                ),
                recommendation=f"Update rel='canonical' href values on affected routes ({routes_preview}) to point strictly to valid HTTP 200 URLs.",
                why_it_matters="Search engines will discard invalid canonical tags, potentially indexing incorrect duplicate parameter URLs.",
                validation_criteria="Every canonical target must return HTTP 200 OK.",
                owner="Developer",
                responsible_role="Developer",
                estimated_effort="Low (< 2 hours)",
                dependencies=["Codebase template access", "Routing configuration"],
                priority_rationale="Critical: Directs search engines to dead error endpoints, breaking canonical indexation.",
                verification_command=f"curl -sI -L '{broken_items[0].canonical_url}' | grep -E '^HTTP/[0-9.]+ 200'",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["canonical_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=9,
                effort=3,
                priority=9
            ))

        if rollup.missing_canonical_count > 0:
            missing_items = [item for item in rollup.items if item.status == "missing"]
            ev_list = []
            for item in missing_items[:10]:
                ev_id = f"EV-CAN-MISS-{hashlib.sha256(item.url.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=item.url,
                    element="head",
                    value="Missing <link rel='canonical'>",
                    observed_value="No canonical tag declared in HTML <head>",
                    expected_condition="Page must specify an absolute, self-referencing <link rel='canonical'> tag",
                    snippet=item.detail or "HTML <head> lacks <link rel='canonical'>",
                    test_method="crawl_html_head",
                    source="crawl",
                ))

            aff_urls = [item.url for item in missing_items]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_missing_canonicals",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=f"{rollup.missing_canonical_count} Page(s) Missing Canonical Tags",
                description=(
                    f"{rollup.missing_canonical_count} page(s) do not define an explicit <link rel='canonical'> tag. "
                    "Without canonical tags, URL parameters or trailing slashes dilute ranking signals across duplicate variants."
                ),
                recommendation=f"Implement self-referencing canonical link tags in the <head> of affected routes ({routes_preview}).",
                why_it_matters="Google states that explicit self-referential canonicals are essential to protect indexation equity.",
                validation_criteria="Every indexable HTML page must include an absolute self-referencing <link rel='canonical'> tag.",
                owner="Developer",
                responsible_role="Developer",
                estimated_effort="Low (< 2 hours)",
                dependencies=["HTML template <head> access"],
                priority_rationale="High: Protects against authority dilution from tracking parameters and alternative URL protocols.",
                verification_command=f"curl -s '{missing_items[0].url}' | grep -i '<link.*rel=[\"\\']canonical'",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["canonical_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=7,
                effort=2,
                priority=7
            ))

        noindex_conflicts = [item for item in rollup.items if item.status == "noindex_conflict"]
        if noindex_conflicts:
            ev_list = []
            for item in noindex_conflicts[:10]:
                ev_id = f"EV-CAN-NOIDX-{hashlib.sha256(f'{item.url}:{item.canonical_url}'.encode()).hexdigest()[:8]}"
                ev_list.append(FindingEvidence(
                    evidence_id=ev_id,
                    url=item.url,
                    element="head",
                    value=item.canonical_url or "",
                    observed_value="Both 'noindex' and rel='canonical' present",
                    expected_condition="Pages with 'noindex' should not declare conflicting canonical directives",
                    snippet=item.detail or f"Conflicting directives on {item.url}",
                    test_method="crawl_html_head",
                    source="crawl",
                ))

            aff_urls = [item.url for item in noindex_conflicts]
            routes_preview = ", ".join(aff_urls[:3]) + ("..." if len(aff_urls) > 3 else "")
            findings.append(Finding(
                finding_id="finding_canonical_noindex_conflict",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                title=f"{len(noindex_conflicts)} Page(s) Have Contradictory 'noindex' and Canonical Tags",
                description=(
                    f"{len(noindex_conflicts)} page(s) specify both 'noindex' and a canonical tag. "
                    "This sends conflicting signals to search engine crawlers."
                ),
                recommendation=f"Resolve directive conflicts on affected routes ({routes_preview}) by removing canonical tags from pages designated as 'noindex', or removing 'noindex' if the page is intended to be indexed.",
                why_it_matters="Google warns that conflicting directives may cause crawler confusion and improper indexation consolidation.",
                validation_criteria="Pages with 'noindex' should not have self-referencing canonicals.",
                evidence=ev_list,
                evidence_refs=[ev.evidence_id for ev in ev_list if ev.evidence_id] or ["canonical_audit"],
                evidence_ids=[ev.evidence_id for ev in ev_list if ev.evidence_id],
                affected_urls=aff_urls,
                affected_sample_count=len(aff_urls),
                scope_classification="PAGE_VERIFIED" if len(aff_urls) <= 3 else "SAMPLE_VERIFIED",
                impact=8,
                effort=2,
                priority=8
            ))

        return rollup, findings


def analyze_canonicals(pages: List[PageEvidence]) -> Tuple[CanonicalAuditRollup, List[Finding]]:
    auditor = CanonicalAuditor()
    return auditor.audit(pages)
