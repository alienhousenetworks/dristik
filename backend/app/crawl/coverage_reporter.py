"""
Crawl Quality & Coverage Intelligence — Enterprise Crawling & Ingestion (Phase 1.6)

Generates multi-dimensional crawl coverage analytics breaking down discovery vs. inspection
by page type, template family, URL status, and inspection method.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawl.orchestration import CrawlProfile
from app.crawl.template_discovery import PageClassifier, StandardPageType, TemplateArchetype
from app.domain.canonical_audit_model import CrawlInventory


class PageTypeCoverageSummary(BaseModel):
    page_type: str
    discovered_count: int
    inspected_count: int
    coverage_pct: float


class TemplateCoverageSummary(BaseModel):
    template_id: str
    template_name: str
    associated_urls_count: int
    sampled_urls_count: int
    coverage_pct: float


class CrawlCoverageReport(BaseModel):
    audit_run_id: str
    domain: str
    profile_used: CrawlProfile = CrawlProfile.STANDARD
    discovered_urls: int = 0
    eligible_urls: int = 0
    crawled_urls: int = 0
    successfully_rendered_urls: int = 0
    failed_urls: int = 0
    excluded_urls: int = 0
    redirected_urls: int = 0
    canonicalized_urls: int = 0
    unreachable_urls: int = 0
    duplicate_content_groups: int = 0
    overall_coverage_pct: float = 0.0
    page_type_coverage: List[PageTypeCoverageSummary] = Field(default_factory=list)
    template_coverage: List[TemplateCoverageSummary] = Field(default_factory=list)
    inspection_method_breakdown: Dict[str, int] = Field(default_factory=dict)
    honest_coverage_statement: str = ""
    full_site_audit: bool = False


class CrawlCoverageReporter:
    """
    Computes accurate multi-dimensional coverage intelligence without collapsing into a single false ratio.
    """

    @classmethod
    def generate_coverage_report(
        cls,
        audit_run_id: str,
        domain: str,
        profile_used: CrawlProfile,
        discovered_urls: List[str],
        crawled_urls: List[Dict[str, Any]],
        failed_urls: Optional[List[str]] = None,
        excluded_urls: Optional[List[str]] = None,
        redirected_urls: Optional[List[str]] = None,
        templates: Optional[List[TemplateArchetype]] = None,
    ) -> Tuple[CrawlCoverageReport, CrawlInventory]:
        discovered_count = len(discovered_urls)
        inspected_count = len(crawled_urls)
        failed_count = len(failed_urls or [])
        excluded_count = len(excluded_urls or [])
        redirected_count = len(redirected_urls or [])

        eligible_count = max(0, discovered_count - excluded_count)
        overall_pct = round((inspected_count / eligible_count) * 100.0, 1) if eligible_count > 0 else 0.0

        rendered_count = sum(1 for c in crawled_urls if c.get("rendered_dom") or c.get("is_rendered") or c.get("rendered_html"))
        crawled_by_url = {str(item.get("url")): item for item in crawled_urls if item.get("url")}

        # Page-type counts come from classified URLs. They are not scaled from the sample ratio.
        type_discovery_counts: Dict[str, int] = {}
        type_inspected_counts: Dict[str, int] = {}

        def _page_type(url: str, item: Optional[Dict[str, Any]] = None) -> str:
            stored = str((item or {}).get("page_type") or "").upper()
            if stored in StandardPageType.__members__:
                return stored
            return PageClassifier.classify(url).value

        for url in discovered_urls:
            item = crawled_by_url.get(url)
            pt = _page_type(url, item)
            type_discovery_counts[pt] = type_discovery_counts.get(pt, 0) + 1
        for url, item in crawled_by_url.items():
            pt = _page_type(url, item)
            type_inspected_counts[pt] = type_inspected_counts.get(pt, 0) + 1
            if url not in discovered_urls:
                type_discovery_counts[pt] = type_discovery_counts.get(pt, 0) + 1

        page_type_summaries: List[PageTypeCoverageSummary] = []
        for pt, ins_cnt in type_inspected_counts.items():
            disc_cnt = max(ins_cnt, type_discovery_counts.get(pt, 0))
            cov_pct = round((ins_cnt / disc_cnt) * 100.0, 1) if disc_cnt > 0 else 0.0
            page_type_summaries.append(PageTypeCoverageSummary(
                page_type=pt,
                discovered_count=disc_cnt,
                inspected_count=ins_cnt,
                coverage_pct=cov_pct,
            ))

        # 2. Template coverage breakdown
        template_summaries: List[TemplateCoverageSummary] = []
        if templates:
            for tpl in templates:
                total_members = len(tpl.member_urls)
                sampled = len([u for u in tpl.member_urls if u in crawled_by_url])
                cov_pct = round((sampled / total_members) * 100.0, 1) if total_members > 0 else 0.0
                template_summaries.append(TemplateCoverageSummary(
                    template_id=tpl.template_id,
                    template_name=tpl.archetype_name,
                    associated_urls_count=total_members,
                    sampled_urls_count=sampled,
                    coverage_pct=cov_pct,
                ))

        # Statement of honesty
        full_site = bool(discovered_count and inspected_count >= eligible_count and eligible_count > 0)
        statement = (
            f"The audit discovered {discovered_count} endpoints across {domain}. "
            f"Using the {profile_used.value} crawl profile, {inspected_count} representative pages "
            f"were inspected ({overall_pct}% sample coverage). "
        )
        if full_site:
            statement += "Every eligible URL in this discovered inventory was inspected. That is not proof that every public URL was found."
        else:
            statement += "This is not a full-site audit. Findings apply only to inspected URLs."

        report = CrawlCoverageReport(
            audit_run_id=audit_run_id,
            domain=domain,
            profile_used=profile_used,
            discovered_urls=discovered_count,
            eligible_urls=eligible_count,
            crawled_urls=inspected_count,
            successfully_rendered_urls=rendered_count,
            failed_urls=failed_count,
            excluded_urls=excluded_count,
            redirected_urls=redirected_count,
            canonicalized_urls=sum(1 for c in crawled_urls if c.get("canonical_target") and c.get("canonical_target") != c.get("url")),
            unreachable_urls=failed_count,
            duplicate_content_groups=0,
            overall_coverage_pct=overall_pct,
            page_type_coverage=page_type_summaries,
            template_coverage=template_summaries,
            inspection_method_breakdown={
                "HTTP_INSPECTION": inspected_count,
                "BROWSER_RENDERED": rendered_count,
            },
            honest_coverage_statement=statement,
            full_site_audit=full_site,
        )

        canonical_inv = CrawlInventory(
            audit_run_id=audit_run_id,
            domain_id=domain,
            inventory_id=f"inv_{audit_run_id[-8:]}",
            discovered_urls_count=discovered_count,
            inspected_urls_count=inspected_count,
            coverage_ratio=round(overall_pct / 100.0, 3),
            is_complete_crawl=inspected_count >= discovered_count and discovered_count > 0,
        )

        return report, canonical_inv
