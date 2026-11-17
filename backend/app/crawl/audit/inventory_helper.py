"""
Dristik AI Authoritative Crawl Inventory Reconciliation Helper.
Provides single source of truth for all crawl counts, denominators, and coverage metrics.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.domain.models import (
    CanonicalUrlEntry,
    CanonicalUrlRegistry,
    CrawlInventory,
    CrawlManifest,
    ExecutiveReport,
)


def _normalize_registry_url(url: str) -> str:
    cleaned = (url or "").strip()
    if len(cleaned) > 1 and cleaned.endswith("/"):
        return cleaned.rstrip("/")
    return cleaned


def get_canonical_crawl_inventory(
    manifest: Optional[Any] = None,
    report: Optional[Any] = None
) -> CrawlInventory:
    """
    Derives an authoritative, single-source-of-truth CrawlInventory
    from manifest, report.crawl_summary, and report.page_reports.
    Guarantees that discovered_total, tested_pages, untested_pages,
    eligible_total, sample_coverage_pct, discovery_coverage_pct, and
    url_coverage_pct are mathematically reconciled.
    """
    if manifest is None and report is not None and getattr(report, "crawl_manifest", None) is not None:
        manifest = report.crawl_manifest

    def _mget(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    pages_crawled = 0
    if report and getattr(report, "page_reports", None):
        pages_crawled = len(report.page_reports)
    elif manifest:
        mpages = _mget(manifest, "pages")
        if mpages and hasattr(mpages, "__len__"):
            pages_crawled = len(mpages)

    crawl_inv_dict = {}
    if manifest and _mget(manifest, "crawl_inventory"):
        ci = _mget(manifest, "crawl_inventory")
        if not hasattr(ci, "_mock_return_value"):
            if isinstance(ci, dict):
                crawl_inv_dict = ci
            elif hasattr(ci, "model_dump"):
                crawl_inv_dict = ci.model_dump()

    crawl_summary = getattr(report, "crawl_summary", {}) if report and isinstance(getattr(report, "crawl_summary", None), dict) else {}
    crawl_budget = _mget(manifest, "crawl_budget") if manifest and isinstance(_mget(manifest, "crawl_budget"), dict) else {}
    crawl_health = _mget(manifest, "crawl_health") if manifest and isinstance(_mget(manifest, "crawl_health"), dict) else {}

    # Discovered total: check all candidate sources
    raw_disc_urls = _mget(manifest, "discovered_urls") if manifest else None
    disc_urls_count = len(raw_disc_urls) if isinstance(raw_disc_urls, (list, set, tuple)) else 0

    disc_candidates = [
        crawl_inv_dict.get("discovered_total"),
        crawl_inv_dict.get("total_unique_discovered"),
        crawl_budget.get("urls_discovered") if isinstance(crawl_budget, dict) else None,
        crawl_summary.get("total_pages_discovered") if isinstance(crawl_summary, dict) else None,
        _mget(manifest, "total_pages_discovered"),
        disc_urls_count,
        pages_crawled,
    ]
    disc_total = max([int(x) for x in disc_candidates if isinstance(x, (int, float)) and not hasattr(x, "_mock_return_value")] or [pages_crawled or 1])

    # Tested pages
    tested_candidates = [
        crawl_inv_dict.get("tested_pages"),
        crawl_inv_dict.get("total_crawled_tested"),
        crawl_budget.get("urls_crawled") if isinstance(crawl_budget, dict) else None,
        crawl_summary.get("total_pages_crawled") if isinstance(crawl_summary, dict) else None,
        _mget(manifest, "total_pages_crawled"),
        pages_crawled,
    ]
    tested_pages = max([int(x) for x in tested_candidates if isinstance(x, (int, float)) and not hasattr(x, "_mock_return_value")] or [pages_crawled])

    # Ensure discovered is at least tested
    if tested_pages > disc_total:
        disc_total = tested_pages

    raw_excluded = crawl_inv_dict.get("excluded_total", getattr(manifest, "excluded_total", 0) if manifest else 0)
    excluded_total = int(raw_excluded) if isinstance(raw_excluded, (int, float)) and not hasattr(raw_excluded, "_mock_return_value") else 0

    raw_eligible = crawl_inv_dict.get("eligible_total")
    if isinstance(raw_eligible, (int, float)) and not hasattr(raw_eligible, "_mock_return_value") and int(raw_eligible) > 0:
        eligible_total = max(tested_pages, int(raw_eligible))
    else:
        eligible_total = max(tested_pages, disc_total - excluded_total)

    untested_pages = max(0, eligible_total - tested_pages)
    raw_failed = crawl_inv_dict.get("failed_total", crawl_inv_dict.get("failed_pages", crawl_inv_dict.get("total_errors", 0)))
    failed_pages = int(raw_failed) if isinstance(raw_failed, (int, float)) and not hasattr(raw_failed, "_mock_return_value") else 0

    # Coverage: sample_coverage_pct and discovery_coverage_pct computed separately
    from app.seo.audit.discovery.coverage import calculate_crawl_coverage
    if eligible_total > 0:
        sample_cov_pct = calculate_crawl_coverage(tested_pages, eligible_total)
    else:
        sample_cov_pct = 100.0 if tested_pages > 0 else 0.0

    if disc_total > 0:
        disc_cov_pct = calculate_crawl_coverage(tested_pages, disc_total)
    else:
        disc_cov_pct = 100.0 if tested_pages > 0 else 0.0

    cov_pct = sample_cov_pct

    # Discovery truncation check
    raw_trunc_manifest = getattr(manifest, "discovery_truncated", False) if manifest else False
    if hasattr(raw_trunc_manifest, "_mock_return_value"):
        raw_trunc_manifest = False
    discovery_truncated = bool(
        raw_trunc_manifest
        or (crawl_budget.get("discovery_truncated") if isinstance(crawl_budget, dict) else False)
        or crawl_inv_dict.get("discovery_truncated")
        or (crawl_health.get("discovery_truncated") if isinstance(crawl_health, dict) else False)
        or (crawl_summary.get("discovery_truncated") if isinstance(crawl_summary, dict) else False)
    )

    # Sampling status: if discovery_truncated is True or tested_pages < disc_total, MUST be SAMPLED_AUDIT
    raw_status = (
        getattr(manifest, "sampling_status", None)
        or crawl_inv_dict.get("sampling_status")
    )
    if discovery_truncated or tested_pages < disc_total:
        sampling_status = "SAMPLED_AUDIT"
    elif isinstance(raw_status, str) and not hasattr(raw_status, "_mock_return_value") and raw_status not in ("NOT_ASSESSED", ""):
        sampling_status = raw_status
    else:
        sampling_status = "FULL_CRAWL"

    rendered_cand = crawl_inv_dict.get("rendered_pages", crawl_inv_dict.get("total_rendered", tested_pages))
    rendered_pages = int(rendered_cand) if isinstance(rendered_cand, (int, float)) and not hasattr(rendered_cand, "_mock_return_value") else tested_pages

    raw_sitemap = crawl_inv_dict.get("discovered_via_sitemap", crawl_inv_dict.get("discovered_via_sitemap_count"))
    if isinstance(raw_sitemap, list):
        discovered_sitemap = len(raw_sitemap)
    elif isinstance(raw_sitemap, (int, float)) and not hasattr(raw_sitemap, "_mock_return_value"):
        discovered_sitemap = int(raw_sitemap)
    else:
        raw_sm_urls = getattr(manifest, "sitemap_urls", None) if manifest else None
        discovered_sitemap = len(raw_sm_urls) if isinstance(raw_sm_urls, (list, set, tuple)) else 0

    raw_links = crawl_inv_dict.get("discovered_via_links")
    if isinstance(raw_links, list):
        discovered_links = len(raw_links)
    elif isinstance(raw_links, (int, float)) and not hasattr(raw_links, "_mock_return_value"):
        discovered_links = int(raw_links)
    else:
        discovered_links = max(0, disc_total - discovered_sitemap)

    raw_seed = crawl_inv_dict.get("seed_urls_count", 1)
    seed_urls_count = int(raw_seed) if isinstance(raw_seed, (int, float)) and not hasattr(raw_seed, "_mock_return_value") else 1

    return CrawlInventory(
        discovered_total=disc_total,
        eligible_total=eligible_total,
        queued_total=disc_total,
        fetched_total=tested_pages + failed_pages,
        rendered_total=rendered_pages,
        analyzed_total=tested_pages,
        excluded_total=excluded_total,
        failed_total=failed_pages,
        untested_total=untested_pages,
        url_coverage_pct=cov_pct,
        sample_coverage_pct=sample_cov_pct,
        discovery_coverage_pct=disc_cov_pct,
        discovery_truncated=discovery_truncated,
        coverage_denominator="eligible_total",
        discovered_via_sitemap=discovered_sitemap,
        discovered_via_links=discovered_links,
        seed_urls_count=seed_urls_count,
        sampling_status=sampling_status,
        tested_pages=tested_pages,
        total_unique_discovered=disc_total,
        total_crawled_tested=tested_pages,
    )


def build_canonical_url_registry(
    report_or_manifest: Any,
    findings: Optional[List[Any]] = None,
) -> CanonicalUrlRegistry:
    """
    Builds a CanonicalUrlRegistry from an ExecutiveReport or CrawlManifest,
    reconciling discovered_urls, pages, untested_discovered_urls, and findings.
    """
    manifest = None
    report = None
    if hasattr(report_or_manifest, "crawl_manifest") or hasattr(report_or_manifest, "page_reports"):
        report = report_or_manifest
        manifest = getattr(report_or_manifest, "crawl_manifest", None)
    else:
        manifest = report_or_manifest

    if findings is None and report is not None:
        findings = list(getattr(report, "findings", None) or [])
    findings = list(findings or [])

    inv = get_canonical_crawl_inventory(manifest=manifest, report=report)
    entries: Dict[str, CanonicalUrlEntry] = {}

    base_url = (
        getattr(manifest, "base_url", None)
        or getattr(report, "website_url", None)
        or ""
    )
    norm_base = _normalize_registry_url(base_url) if base_url else ""

    raw_sm = getattr(manifest, "sitemap_urls", None) or getattr(manifest, "discovered_via_sitemap", None) or []
    sitemap_norm_set = {_normalize_registry_url(u) for u in raw_sm if isinstance(u, str) and u.strip()}

    def _source_for(u: str) -> str:
        nu = _normalize_registry_url(u)
        if norm_base and nu == norm_base:
            return "seed"
        if nu in sitemap_norm_set:
            return "sitemap"
        return "link"

    # 1. Populate discovered_urls and untested_discovered_urls
    disc_urls = list(getattr(manifest, "discovered_urls", None) or []) if manifest else []
    untested_urls = list(getattr(manifest, "untested_discovered_urls", None) or []) if manifest else []
    for u in disc_urls + untested_urls:
        if not isinstance(u, str) or not u.strip():
            continue
        nu = _normalize_registry_url(u)
        if nu not in entries:
            entries[nu] = CanonicalUrlEntry(
                url=u.strip(),
                normalized_url=nu,
                status="discovered_untested",
                source=_source_for(u),
            )

    # 2. Populate tested pages
    pages = list(getattr(manifest, "pages", None) or []) if manifest else []
    if not pages and report is not None:
        pages = list(getattr(report, "page_reports", None) or [])
    for p in pages:
        u = getattr(p, "url", None)
        if not isinstance(u, str) or not u.strip():
            continue
        nu = _normalize_registry_url(u)
        http_status = getattr(p, "status_code", 200)
        ttfb_val = getattr(p, "ttfb_ms", None)
        if ttfb_val is None and getattr(p, "ux", None) is not None:
            ttfb_val = getattr(p.ux, "ttfb_ms", None)
        origin_ttfb = getattr(p, "origin_http_ttfb_ms", None)
        entries[nu] = CanonicalUrlEntry(
            url=u.strip(),
            normalized_url=nu,
            status="tested",
            source=_source_for(u),
            http_status=int(http_status) if isinstance(http_status, (int, float)) else 200,
            ttfb_ms=float(ttfb_val) if isinstance(ttfb_val, (int, float)) else None,
            origin_http_ttfb_ms=float(origin_ttfb) if isinstance(origin_ttfb, (int, float)) else None,
        )

    # 3. Populate failed URLs from crawl_health.broken_links if present
    crawl_health = getattr(manifest, "crawl_health", None) if manifest else None
    broken_links = crawl_health.get("broken_links", []) if isinstance(crawl_health, dict) else []
    for bl in (broken_links or []):
        if isinstance(bl, dict):
            u = bl.get("url")
            if isinstance(u, str) and u.strip():
                nu = _normalize_registry_url(u)
                if nu not in entries or entries[nu].status != "tested":
                    entries[nu] = CanonicalUrlEntry(
                        url=u.strip(),
                        normalized_url=nu,
                        status="failed",
                        source=_source_for(u),
                    )

    # 4. Link findings and evidence IDs to URL entries
    for f in findings:
        f_id = getattr(f, "finding_id", None)
        aff_urls = list(getattr(f, "affected_urls", None) or [])
        for ev in list(getattr(f, "evidence", None) or []):
            ev_u = getattr(ev, "url", None) if not isinstance(ev, dict) else ev.get("url")
            ev_id = getattr(ev, "evidence_id", None) if not isinstance(ev, dict) else ev.get("evidence_id")
            if isinstance(ev_u, str) and ev_u.strip():
                if ev_u.strip() not in aff_urls:
                    aff_urls.append(ev_u.strip())
                nu = _normalize_registry_url(ev_u)
                if nu not in entries:
                    entries[nu] = CanonicalUrlEntry(
                        url=ev_u.strip(),
                        normalized_url=nu,
                        status="tested",
                        source=_source_for(ev_u),
                    )
                if isinstance(ev_id, str) and ev_id.strip() and ev_id.strip() not in entries[nu].evidence_ids:
                    entries[nu].evidence_ids.append(ev_id.strip())
        for u in aff_urls:
            if not isinstance(u, str) or not u.strip():
                continue
            nu = _normalize_registry_url(u)
            if nu not in entries:
                entries[nu] = CanonicalUrlEntry(
                    url=u.strip(),
                    normalized_url=nu,
                    status="tested",
                    source=_source_for(u),
                )
            if isinstance(f_id, str) and f_id.strip() and f_id.strip() not in entries[nu].finding_ids:
                entries[nu].finding_ids.append(f_id.strip())
            for eid in list(getattr(f, "evidence_ids", None) or getattr(f, "evidence_refs", None) or []):
                if isinstance(eid, str) and eid.strip() and eid.strip() not in entries[nu].evidence_ids:
                    entries[nu].evidence_ids.append(eid.strip())

    return CanonicalUrlRegistry(
        entries=entries,
        discovered_total=inv.discovered_total,
        eligible_total=inv.eligible_total,
        tested_total=inv.tested_pages,
        failed_total=inv.failed_total,
        excluded_total=inv.excluded_total,
    )
