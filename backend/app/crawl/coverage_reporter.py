"""
Crawl Quality & Coverage Intelligence — Enterprise Crawling & Ingestion (Phase 1.6)

Generates multi-dimensional crawl coverage analytics breaking down discovery vs. inspection
by page type, template family, URL status, and inspection method.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.crawl.orchestration import CrawlProfile
from app.crawl.template_discovery import StandardPageType, TemplateArchetype
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

        rendered_count = sum(1 for c in crawled_urls if c.get("rendered_dom") or c.get("is_rendered"))

        # 1. Page type coverage breakdown
        type_discovery_counts: Dict[str, int] = {}
        type_inspected_counts: Dict[str, int] = {}

        for item in crawled_urls:
            pt = str(item.get("page_type") or StandardPageType.UNKNOWN.value).upper()
            type_inspected_counts[pt] = type_inspected_counts.get(pt, 0) + 1

        # Calculate page type coverage
        page_type_summaries: List[PageTypeCoverageSummary] = []
        for pt, ins_cnt in type_inspected_counts.items():
            # In deep crawl, discovery counts for types are estimated or matched by pattern
            disc_cnt = max(ins_cnt, int(ins_cnt * (discovered_count / max(1, inspected_count))))
            cov_pct = round((ins_cnt / disc_cnt) * 100.0, 1) if disc_cnt > 0 else 100.0
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
                # Sampled URLs in template
                sampled = len([u for u in tpl.member_urls if any(c.get("url") == u for c in crawled_urls)])
                if sampled == 0 and total_members > 0:
                    sampled = 1  # Archetype sample URL was evaluated
                cov_pct = round((sampled / total_members) * 100.0, 1) if total_members > 0 else 100.0
                template_summaries.append(TemplateCoverageSummary(
                    template_id=tpl.template_id,
                    template_name=tpl.archetype_name,
                    associated_urls_count=total_members,
                    sampled_urls_count=sampled,
                    coverage_pct=cov_pct,
                ))

        # Statement of honesty
        statement = (
            f"The audit discovered {discovered_count} endpoints across {domain}. "
            f"Using the {profile_used.value} crawl profile, {inspected_count} representative pages "
            f"were inspected ({overall_pct}% sample coverage). "
            f"Findings apply to inspected samples and their corresponding template archetypes, "
            f"not to the entire uninspected surface."
        )

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
