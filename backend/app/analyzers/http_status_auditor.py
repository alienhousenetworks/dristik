"""
Dristik AI HTTP Status Code & Broken Link Auditor
Classifies crawled URLs into status buckets:
- 2xx Success (HTTP 200)
- 3xx Redirections (HTTP 301, 302, 307, 308)
- 4xx Client Errors (HTTP 404, 403, 410)
- 5xx Server Errors (HTTP 500, 502, 503)
Surfaces source URLs and anchor text for all broken links (Industry Standard Screaming Frog model).
"""
from typing import List, Tuple
from app.domain.models import PageEvidence, HttpStatusBreakdown, HttpStatusItem, BrokenLinkRecord, Finding, FindingEvidence
from app.domain.enums import Category, Severity


class HttpStatusAuditor:
    def audit(
        self,
        pages: List[PageEvidence],
        broken_links_raw: Optional[List[dict]] = None
    ) -> Tuple[HttpStatusBreakdown, List[Finding]]:
        if not pages:
            return HttpStatusBreakdown(), []

        rollup = HttpStatusBreakdown(total_urls_checked=len(pages))
        findings: List[Finding] = []

        # Map internal inlinks
        inlink_counts: dict = {}
        for p in pages:
            for l in (p.internal_links or []):
                norm = l.rstrip("/")
                inlink_counts[norm] = inlink_counts.get(norm, 0) + 1

        for p in pages:
            code = p.status_code
            clean_url = p.url.rstrip("/")
            inlinks = inlink_counts.get(clean_url, 0)

            if 200 <= code < 300:
                rollup.count_2xx += 1
                rollup.pages_2xx.append(HttpStatusItem(
                    url=p.url,
                    status_code=code,
                    status_class="2xx",
                    status_text="OK",
                    inlinks_count=inlinks
                ))
            elif 300 <= code < 400:
                rollup.count_3xx += 1
                dest = p.final_url or (p.redirect_chain[-1].get("location") if p.redirect_chain else None)
                rollup.pages_3xx.append(HttpStatusItem(
                    url=p.url,
                    status_code=code,
                    status_class="3xx",
                    status_text="Redirect",
                    redirect_target=dest,
                    inlinks_count=inlinks
                ))
            elif 400 <= code < 500:
                rollup.count_4xx += 1
                rollup.pages_4xx.append(HttpStatusItem(
                    url=p.url,
                    status_code=code,
                    status_class="4xx",
                    status_text="Client Error",
                    inlinks_count=inlinks
                ))
            else:
                rollup.count_5xx += 1
                rollup.pages_5xx.append(HttpStatusItem(
                    url=p.url,
                    status_code=code,
                    status_class="5xx",
                    status_text="Server Error",
                    inlinks_count=inlinks
                ))

        # Broken links collection from raw crawl errors
        if broken_links_raw:
            for bl in broken_links_raw:
                rollup.broken_links.append(BrokenLinkRecord(
                    source_url=bl.get("source_url") or bl.get("page_url") or "",
                    target_url=bl.get("url") or bl.get("target_url") or "",
                    anchor_text=bl.get("anchor") or bl.get("anchor_text") or "",
                    status_code=bl.get("status") or 404,
                    error_type=bl.get("error") or "404 Not Found"
                ))

        total = max(rollup.total_urls_checked, 1)
        err_penalty = (rollup.count_4xx * 25.0) + (rollup.count_5xx * 35.0) + (rollup.count_3xx * 4.0)
        rollup.status_health_score = max(0.0, min(100.0, round(100.0 - (err_penalty / total * 10), 1)))

        rollup.summary = (
            f"Audited {total} URLs: {rollup.count_2xx} HTTP 2xx ({round(rollup.count_2xx/total*100, 1)}%), "
            f"{rollup.count_3xx} Redirects (3xx), {rollup.count_4xx} Client Errors (4xx), {rollup.count_5xx} Server Errors (5xx)."
        )

        if rollup.count_4xx > 0:
            findings.append(Finding(
                finding_id="finding_http_4xx_errors",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title=f"{rollup.count_4xx} HTTP 4xx Client Error(s) Encountered",
                description=(
                    f"The crawler recorded {rollup.count_4xx} URL(s) returning HTTP 4xx errors (e.g. 404 Not Found, 403 Forbidden). "
                    "Broken pages waste crawl budget, cause negative user experience, and leak PageRank."
                ),
                recommendation="Fix broken links pointing to 404 pages or implement 301 redirects to relevant live pages.",
                why_it_matters="Search engines demote sites with high 404 rates and remove unresolvable URLs from the index.",
                validation_criteria="Every linked internal URL must resolve with HTTP 200 OK.",
                evidence=[
                    FindingEvidence(
                        url=item.url,
                        element="HTTP Status",
                        value=f"HTTP {item.status_code}",
                        snippet=f"URL returns HTTP {item.status_code}",
                        source="crawl"
                    )
                    for item in rollup.pages_4xx
                ],
                evidence_refs=["http_status_audit"],
                impact=9,
                effort=3,
                priority=9
            ))

        if rollup.count_5xx > 0:
            findings.append(Finding(
                finding_id="finding_http_5xx_errors",
                category=Category.TECHNICAL_SEO,
                severity=Severity.CRITICAL,
                title=f"{rollup.count_5xx} HTTP 5xx Server Error(s) Encountered",
                description=(
                    f"The crawler encountered {rollup.count_5xx} server errors (HTTP 5xx). "
                    "Server errors indicate backend crashes or timeouts that completely block Googlebot."
                ),
                recommendation="Investigate server logs and application error traces to resolve backend server failures.",
                why_it_matters="Persistent 5xx errors will cause Googlebot to slow crawl rates and de-index affected URLs.",
                validation_criteria="Server must not return 5xx errors under ordinary crawl load.",
                evidence=[
                    FindingEvidence(
                        url=item.url,
                        element="HTTP Status",
                        value=f"HTTP {item.status_code}",
                        snippet=f"URL returns HTTP {item.status_code}",
                        source="crawl"
                    )
                    for item in rollup.pages_5xx
                ],
                evidence_refs=["http_status_audit"],
                impact=10,
                effort=5,
                priority=10
            ))

        return rollup, findings


def analyze_http_statuses(
    pages: List[PageEvidence],
    broken_links_raw: Optional[List[dict]] = None
) -> Tuple[HttpStatusBreakdown, List[Finding]]:
    auditor = HttpStatusAuditor()
    return auditor.audit(pages, broken_links_raw=broken_links_raw)
