"""
Dristik AI Canonical & Redirect Consistency Engine
Deterministic analysis of HTTP redirect chains and HTML canonical tags.
Flags redirect loops, excessive hops, cross-domain bounces, canonical-to-redirect
anti-patterns, and canonical target mismatches backed by typed EvidenceRef.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from app.domain.enums import Category, Severity, VerificationStatus
from app.domain.models import CrawlManifest, Finding, FindingEvidence, PageEvidence
from app.evidence.models import EvidenceRef

logger = logging.getLogger("dristik.analyzers.canonical_redirect")


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
    return f"{scheme}://{netloc}{path}"


def _compute_hash(data: Any) -> str:
    s = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class CanonicalRedirectConsistencyAnalyzer:
    """
    Evaluates CrawlManifest redirect chains and PageEvidence canonical directives
    to surface search engine crawling bottlenecks and indexing discrepancies.
    """

    def analyze(
        self,
        manifest: CrawlManifest,
        pages: Optional[List[PageEvidence]] = None
    ) -> Dict[str, Any]:
        pages_list = pages or manifest.pages or []
        chains = manifest.redirect_chains or []

        findings: List[Finding] = []
        url_to_page: Dict[str, PageEvidence] = {
            _normalize_url(p.url): p for p in pages_list if p.url
        }

        # Build mapping of initial_url -> chain for quick lookup
        chain_by_initial: Dict[str, Dict[str, Any]] = {}
        for ch in chains:
            init = _normalize_url(ch.get("initial_url"))
            if init:
                chain_by_initial[init] = ch

        total_loops = 0
        total_excessive = 0
        total_cross_domain = 0
        total_non_canonical_targets = 0
        total_canonical_to_redirect = 0
        total_missing_canonicals = 0

        # 1. Audit redirect chains
        for ch in chains:
            init_url = ch.get("initial_url", "")
            final_url = ch.get("final_url", "")
            hops = ch.get("hops", [])
            hop_count = ch.get("hop_count", len(hops))

            # A. Check for redirect loops
            visited_urls: List[str] = [_normalize_url(init_url)]
            has_loop = False
            loop_pivot = ""
            for hop in hops:
                dest = _normalize_url(hop.get("destination", ""))
                if dest in visited_urls:
                    has_loop = True
                    loop_pivot = dest
                    break
                visited_urls.append(dest)

            if has_loop:
                total_loops += 1
                ev_hash = _compute_hash({"chain": ch, "loop_pivot": loop_pivot})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"redr_loop_{total_loops}",
                    evidence_hash=ev_hash,
                    url=init_url,
                    snippet=f"Loop back to {loop_pivot} in hops: {hops}",
                    metadata={"chain": ch, "loop_pivot": loop_pivot}
                )
                findings.append(Finding(
                    finding_id=f"finding_redirect_loop_{total_loops}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.CRITICAL,
                    title="Infinite HTTP Redirect Loop Detected",
                    description=(
                        f"URL '{init_url}' triggers a circular redirect loop returning to '{loop_pivot}'. "
                        "Search engines and web browsers will abort requests after hitting client limits."
                    ),
                    recommendation=f"Update web server or routing config so '{init_url}' directly serves 200 OK or 301 to '{final_url}'.",
                    why_it_matters="Redirect loops cause 100% crawl failure and prevent search engine bots from discovering or indexing content.",
                    validation_criteria=f"Direct HTTP fetch to {init_url} must return HTTP 200 without repeating destination URLs.",
                    evidence=[FindingEvidence(
                        url=init_url,
                        element="http_header",
                        value=f"Circular redirect loop returning to {loop_pivot}",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=10,
                    effort=3,
                    priority=10,
                ))

            # B. Check for excessive hops (> 2 hops)
            if hop_count > 2 and not has_loop:
                total_excessive += 1
                ev_hash = _compute_hash({"hops": hops, "hop_count": hop_count})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"redr_excessive_{total_excessive}",
                    evidence_hash=ev_hash,
                    url=init_url,
                    snippet=f"{hop_count} hops: {' -> '.join(h.get('destination', '') for h in hops)}",
                    metadata={"hops": hops, "hop_count": hop_count}
                )
                findings.append(Finding(
                    finding_id=f"finding_redirect_excessive_{total_excessive}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.HIGH,
                    title=f"Excessive Redirect Chain ({hop_count} Hops)",
                    description=(
                        f"URL '{init_url}' undergoes {hop_count} intermediate redirects before reaching '{final_url}'. "
                        "Multi-hop chains drain crawl budget and add unnecessary latency."
                    ),
                    recommendation=f"Point internal links and redirects for '{init_url}' directly to final URL '{final_url}'.",
                    why_it_matters="Googlebot may abandon chains deeper than 2-3 hops, causing link equity loss and increased crawl latency.",
                    validation_criteria=f"HTTP request to {init_url} must resolve to {final_url} in at most 1 redirect hop.",
                    evidence=[FindingEvidence(
                        url=init_url,
                        element="http_header",
                        value=f"Multi-hop redirect chain ({hop_count} hops)",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=7,
                    effort=2,
                    priority=8,
                ))

            # C. Check for cross-domain bounces
            hosts_in_chain = [urlparse(init_url).netloc.lower()]
            for hop in hops:
                h_dest = hop.get("destination", "")
                if h_dest:
                    hosts_in_chain.append(urlparse(h_dest).netloc.lower())
            distinct_hosts = list(dict.fromkeys(h for h in hosts_in_chain if h))
            if len(distinct_hosts) > 2 or (len(distinct_hosts) == 2 and hosts_in_chain[0] == hosts_in_chain[-1]):
                total_cross_domain += 1
                ev_hash = _compute_hash({"hosts": hosts_in_chain})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"redr_cross_domain_{total_cross_domain}",
                    evidence_hash=ev_hash,
                    url=init_url,
                    snippet=f"Cross-domain bounce: {' -> '.join(distinct_hosts)}",
                    metadata={"hosts": hosts_in_chain}
                )
                findings.append(Finding(
                    finding_id=f"finding_redirect_cross_domain_{total_cross_domain}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.HIGH,
                    title="Cross-Domain Redirect Bounce Detected",
                    description=(
                        f"Redirect chain for '{init_url}' bounces across multiple external hosts: {distinct_hosts}. "
                        "Cross-origin redirects degrade trust and break referrer data."
                    ),
                    recommendation=f"Serve content directly on final host without intermediary bounces through '{distinct_hosts[1]}'.",
                    why_it_matters="Bouncing across third-party hosts increases connection setup times (TLS handshake per origin) and risks TLS/SSRF failures.",
                    validation_criteria=f"Requests to {init_url} should redirect only within the canonical host or directly to final host.",
                    evidence=[FindingEvidence(
                        url=init_url,
                        element="http_header",
                        value=f"Cross-domain hops: {distinct_hosts}",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=8,
                    effort=4,
                    priority=8,
                ))

            # D. Check if final URL's canonical differs from final URL
            norm_final = _normalize_url(final_url)
            landing_page = url_to_page.get(norm_final)
            if landing_page and landing_page.canonical_url:
                norm_canon = _normalize_url(landing_page.canonical_url)
                if norm_canon and norm_canon != norm_final:
                    total_non_canonical_targets += 1
                    ev_hash = _compute_hash({
                        "init": init_url,
                        "final": final_url,
                        "canonical": landing_page.canonical_url
                    })
                    ev_ref = EvidenceRef(
                        source_type="crawl",
                        source_id=f"redr_non_canonical_{total_non_canonical_targets}",
                        evidence_hash=ev_hash,
                        url=final_url,
                        snippet=f"Final landing: {final_url} != Canonical: {landing_page.canonical_url}",
                        metadata={"final_url": final_url, "canonical": landing_page.canonical_url}
                    )
                    findings.append(Finding(
                        finding_id=f"finding_redirect_non_canonical_{total_non_canonical_targets}",
                        category=Category.TECHNICAL_SEO,
                        severity=Severity.HIGH,
                        title="Redirect Chain Ends on Non-Canonical URL",
                        description=(
                            f"Redirect for '{init_url}' lands on '{final_url}', which declares a different "
                            f"canonical URL '{landing_page.canonical_url}'. This creates mixed indexing signals."
                        ),
                        recommendation=(
                            f"Update redirect from '{init_url}' to point directly to the canonical URL "
                            f"'{landing_page.canonical_url}', or make '{final_url}' self-canonical."
                        ),
                        why_it_matters="Directing redirects to URLs that then canonize elsewhere delays indexing and causes link equity leakage.",
                        validation_criteria=f"Redirect chain from {init_url} must land directly on canonical target {landing_page.canonical_url}.",
                        evidence=[FindingEvidence(
                            url=final_url,
                            element="link[rel=canonical]",
                            value=landing_page.canonical_url,
                            source="crawl",
                            evidence_ref=ev_ref,
                        )],
                        evidence_refs=[ev_ref.source_id],
                        evidence_ref_objects=[ev_ref],
                        impact=8,
                        effort=2,
                        priority=8,
                    ))

        # 2. Audit PageEvidence canonical directives
        for page in pages_list:
            if not page.url:
                continue
            norm_url = _normalize_url(page.url)

            # Check if canonical is missing
            if not page.canonical_url:
                total_missing_canonicals += 1
                ev_hash = _compute_hash({"url": page.url, "canonical": None})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"canon_missing_{total_missing_canonicals}",
                    evidence_hash=ev_hash,
                    url=page.url,
                    selector="head",
                    snippet="<link rel='canonical'> not found",
                    metadata={"url": page.url}
                )
                findings.append(Finding(
                    finding_id=f"finding_canonical_missing_{total_missing_canonicals}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.MEDIUM,
                    title="Missing Canonical Tag on Indexable Page",
                    description=f"Page '{page.url}' does not declare a canonical URL tag.",
                    recommendation=f"Add a self-referencing canonical tag: <link rel='canonical' href='{page.url}'> in the <head>.",
                    why_it_matters="Without explicit canonical tags, search engines may treat URL parameters or HTTP/HTTPS variations as duplicate content.",
                    validation_criteria=f"<head> of {page.url} must contain a valid <link rel='canonical' href='{page.url}'>.",
                    evidence=[FindingEvidence(
                        url=page.url,
                        element="head",
                        value="Missing <link rel='canonical'>",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=5,
                    effort=1,
                    priority=5,
                ))
                continue

            # Check if canonical is relative or malformed
            c_raw = page.canonical_url.strip()
            if not (c_raw.startswith("http://") or c_raw.startswith("https://")):
                ev_hash = _compute_hash({"url": page.url, "canonical": c_raw})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"canon_syntax_{page.url}",
                    evidence_hash=ev_hash,
                    url=page.url,
                    selector="link[rel=canonical]",
                    snippet=f"href='{c_raw}'",
                    metadata={"canonical": c_raw}
                )
                findings.append(Finding(
                    finding_id=f"finding_canonical_syntax_{hashlib.md5(page.url.encode()).hexdigest()[:8]}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.HIGH,
                    title="Relative or Malformed Canonical URL",
                    description=f"Page '{page.url}' specifies a non-absolute canonical href: '{c_raw}'.",
                    recommendation="Canonical URLs must always be absolute URLs including scheme (https://) and domain name.",
                    why_it_matters="Search engines may misinterpret relative canonical links, leading to unexpected indexation drop-offs.",
                    validation_criteria="Canonical link href must begin with https:// followed by the canonical domain and path.",
                    evidence=[FindingEvidence(
                        url=page.url,
                        element="link[rel=canonical]",
                        value=c_raw,
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=7,
                    effort=1,
                    priority=7,
                ))

            # Check if canonical points to a URL that itself redirects
            norm_canon = _normalize_url(page.canonical_url)
            if norm_canon in chain_by_initial:
                ch = chain_by_initial[norm_canon]
                total_canonical_to_redirect += 1
                ev_hash = _compute_hash({"url": page.url, "canonical": page.canonical_url, "chain": ch})
                ev_ref = EvidenceRef(
                    source_type="crawl",
                    source_id=f"canon_to_redr_{total_canonical_to_redirect}",
                    evidence_hash=ev_hash,
                    url=page.url,
                    selector="link[rel=canonical]",
                    snippet=f"Canonical points to redirecting URL: {page.canonical_url} -> {ch.get('final_url')}",
                    metadata={"canonical": page.canonical_url, "redirect_chain": ch}
                )
                findings.append(Finding(
                    finding_id=f"finding_canonical_to_redirect_{total_canonical_to_redirect}",
                    category=Category.TECHNICAL_SEO,
                    severity=Severity.HIGH,
                    title="Canonical URL Points to a Redirecting Page",
                    description=(
                        f"Page '{page.url}' specifies canonical '{page.canonical_url}', which itself redirects "
                        f"to '{ch.get('final_url')}'. Canonical targets should always resolve directly with HTTP 200."
                    ),
                    recommendation=f"Update canonical URL to target the final destination '{ch.get('final_url')}'.",
                    why_it_matters="Google recommends against canonical URLs that return redirects; it causes confusion in canonical cluster assignment.",
                    validation_criteria=f"Fetching canonical URL {page.canonical_url} must return HTTP 200 without redirecting.",
                    evidence=[FindingEvidence(
                        url=page.url,
                        element="link[rel=canonical]",
                        value=f"{page.canonical_url} -> {ch.get('final_url')}",
                        source="crawl",
                        evidence_ref=ev_ref,
                    )],
                    evidence_refs=[ev_ref.source_id],
                    evidence_ref_objects=[ev_ref],
                    impact=7,
                    effort=2,
                    priority=7,
                ))

        summary = {
            "total_chains_inspected": len(chains),
            "total_pages_inspected": len(pages_list),
            "redirect_loops": total_loops,
            "excessive_chains": total_excessive,
            "cross_domain_bounces": total_cross_domain,
            "non_canonical_redirect_targets": total_non_canonical_targets,
            "canonical_points_to_redirect": total_canonical_to_redirect,
            "missing_canonicals": total_missing_canonicals,
            "findings_count": len(findings),
        }

        return {
            "summary": summary,
            "findings": findings,
        }
