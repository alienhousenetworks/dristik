"""
Dristik AI Authoritative Crawl Inventory Reconciliation Helper.
Provides single source of truth for all crawl counts, denominators, and coverage metrics.
"""
from __future__ import annotations

from typing import Any, Optional
from app.domain.models import CrawlInventory, CrawlManifest, ExecutiveReport


def get_canonical_crawl_inventory(
    manifest: Optional[Any] = None,
    report: Optional[Any] = None
) -> CrawlInventory:
    """
    Derives an authoritative, single-source-of-truth CrawlInventory
    from manifest, report.crawl_summary, and report.page_reports.
    Guarantees that discovered_total, tested_pages, untested_pages,
    eligible_total, and url_coverage_pct are mathematically reconciled.
    """
    pages_crawled = 0
    if report and getattr(report, "page_reports", None):
        pages_crawled = len(report.page_reports)
    elif manifest and getattr(manifest, "pages", None):
        pages_crawled = len(manifest.pages)

    crawl_inv_dict = {}
    if manifest and getattr(manifest, "crawl_inventory", None):
        ci = manifest.crawl_inventory
        if not hasattr(ci, "_mock_return_value"):
            if isinstance(ci, dict):
                crawl_inv_dict = ci
            elif hasattr(ci, "model_dump"):
                crawl_inv_dict = ci.model_dump()

    crawl_summary = getattr(report, "crawl_summary", {}) if report and isinstance(getattr(report, "crawl_summary", None), dict) else {}
    crawl_budget = getattr(manifest, "crawl_budget", {}) if manifest and isinstance(getattr(manifest, "crawl_budget", None), dict) else {}

    # Discovered total: check all candidate sources
    raw_disc_urls = getattr(manifest, "discovered_urls", None) if manifest else None
    disc_urls_count = len(raw_disc_urls) if isinstance(raw_disc_urls, (list, set, tuple)) else 0

    disc_candidates = [
        crawl_inv_dict.get("discovered_total"),
        crawl_inv_dict.get("total_unique_discovered"),
        crawl_budget.get("urls_discovered") if isinstance(crawl_budget, dict) else None,
        crawl_summary.get("total_pages_discovered") if isinstance(crawl_summary, dict) else None,
        getattr(manifest, "total_pages_discovered", None),
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
        getattr(manifest, "total_pages_crawled", None),
        pages_crawled,
    ]
    tested_pages = max([int(x) for x in tested_candidates if isinstance(x, (int, float)) and not hasattr(x, "_mock_return_value")] or [pages_crawled])

    # Ensure discovered is at least tested
    if tested_pages > disc_total:
        disc_total = tested_pages

    eligible_total = disc_total
    untested_pages = max(0, eligible_total - tested_pages)
    raw_failed = crawl_inv_dict.get("failed_pages", crawl_inv_dict.get("total_errors", 0))
    failed_pages = int(raw_failed) if isinstance(raw_failed, (int, float)) and not hasattr(raw_failed, "_mock_return_value") else 0

    # Coverage
    if eligible_total > 0:
        cov_pct = round((tested_pages / eligible_total) * 100.0, 1)
    else:
        cov_pct = 100.0 if tested_pages > 0 else 0.0

    # Sampling status
    raw_status = (
        getattr(manifest, "sampling_status", None)
        or crawl_inv_dict.get("sampling_status")
    )
    if isinstance(raw_status, str) and not hasattr(raw_status, "_mock_return_value"):
        sampling_status = raw_status
    else:
        sampling_status = "SAMPLED_AUDIT" if disc_total > tested_pages else "FULL_CRAWL"

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
        excluded_total=0,
        failed_total=failed_pages,
        untested_total=untested_pages,
        url_coverage_pct=cov_pct,
        coverage_denominator="eligible_total",
        discovered_via_sitemap=discovered_sitemap,
        discovered_via_links=discovered_links,
        seed_urls_count=seed_urls_count,
        sampling_status=sampling_status,
        tested_pages=tested_pages,
        total_unique_discovered=disc_total,
        total_crawled_tested=tested_pages,
    )
