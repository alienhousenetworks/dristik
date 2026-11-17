"""
M1.2 & M1.3 Unit Tests:
- Crawl Coverage Calculation, Denominators & Canonical URL Registry
- TTFB Statistics, Outlier Isolation, Browser/Crawler Timing & Honest CWV
- Evidence-to-URL Reconciliation & Root-Cause Linking across Finding, DecisionEngine,
  FindingRegistry, FindingDeduplicator, CrossChapterConsistencyEngine, and AuditRepository
"""
from __future__ import annotations

import os
import pytest
from types import SimpleNamespace

from app.seo.audit.discovery.coverage import calculate_crawl_coverage
from app.crawl.audit.inventory_helper import (
    build_canonical_url_registry,
    get_canonical_crawl_inventory,
)
from app.crawl.crawler import CrawlerService, compute_ttfb_stats
from app.crawl.analyzers.lighthouse import LighthouseRunner
from app.connectors.crux.connector import resolve_crux_api_key
from app.domain.enums import Category, Severity, VerificationStatus, ClaimType
from app.domain.models import (
    BusinessProfile,
    CategoryScore,
    Claim,
    CrawlManifest,
    ExecutiveReport,
    Finding,
    FindingEvidence,
    MetaBucketItem,
    MetaBucketRollup,
    OverallScoreResult,
    PageEvidence,
    PageReport,
    ThreeWayComparison,
)
from app.orchestration.cognition.decision_engine import DecisionEngine
from app.orchestration.cognition.finding_registry import FindingRegistry
from app.remediation.deduplicator import FindingDeduplicator, build_root_cause_links
from app.crawl.audit.consistency_engine import CrossChapterConsistencyEngine
from app.seo.agents.performance_agent import PerformanceAgent
from app.db.repository import AuditRepository


def test_coverage_calculation_never_zero_for_positive_crawled_and_truncation():
    # 5 / 504 -> 1.0%, 1 / 2000 -> 0.1%, 0 / 504 -> 0.0%
    assert calculate_crawl_coverage(5, 504) == 1.0
    assert calculate_crawl_coverage(1, 2000) == 0.1
    assert calculate_crawl_coverage(0, 504) == 0.0
    assert calculate_crawl_coverage(5, 0) == 0.0

    # Inventory helper with 5 crawled out of 504 discovered
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        total_pages_discovered=504,
        total_pages_crawled=5,
        pages=[PageEvidence(url=f"https://example.com/p{i}", status_code=200) for i in range(5)],
        discovered_urls=[f"https://example.com/p{i}" for i in range(504)],
    )
    inv = get_canonical_crawl_inventory(manifest=manifest)
    assert inv.discovered_total == 504
    assert inv.eligible_total == 504
    assert inv.tested_pages == 5
    assert inv.sample_coverage_pct == 1.0
    assert inv.discovery_coverage_pct == 1.0
    assert inv.url_coverage_pct == 1.0
    assert inv.sampling_status == "SAMPLED_AUDIT"

    # Even if tested_pages == discovered_total, discovery_truncated=True forces SAMPLED_AUDIT
    trunc_manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com",
        total_pages_discovered=10,
        total_pages_crawled=10,
        pages=[PageEvidence(url=f"https://example.com/p{i}", status_code=200) for i in range(10)],
        discovery_truncated=True,
        sampling_status="FULL_CRAWL",
        crawl_budget={"discovery_truncated": True, "urls_discovered": 10, "urls_crawled": 10},
    )
    trunc_inv = get_canonical_crawl_inventory(manifest=trunc_manifest)
    assert trunc_inv.discovery_truncated is True
    assert trunc_inv.sampling_status == "SAMPLED_AUDIT"


def test_ttfb_stats_outlier_isolation_and_explanation():
    ttfb_values = [345, 252, 36208, 288, 248]
    urls = [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/services",
        "https://example.com/work",
        "https://example.com/contact",
    ]
    pages = [
        PageEvidence(url=u, status_code=200, ttfb_ms=float(val))
        for u, val in zip(urls, ttfb_values)
    ]

    stats = compute_ttfb_stats(pages)
    assert stats.mean_ms == pytest.approx(7468.2, abs=0.1)
    assert stats.median_ms == 288.0
    assert stats.max_ms == 36208.0
    assert stats.min_ms == 248.0
    assert stats.outlier_urls == ["https://example.com/services"]
    assert stats.outlier_explanation is not None
    assert "https://example.com/services" in stats.outlier_explanation
    assert "36208" in stats.outlier_explanation
    assert "288" in stats.outlier_explanation
    assert pages[2].ttfb_outlier_reason == stats.outlier_explanation

    # Verify CrawlerService._build_crawl_manifest populates manifest.ttfb_stats and crawl_health
    crawler = CrawlerService()
    manifest = crawler._build_crawl_manifest(
        base_domain="example.com",
        base_url="https://example.com/",
        crawled_pages=pages,
        total_discovered=504,
        sitemap_found=True,
        sitemap_url="https://example.com/sitemap.xml",
        robots_txt_found=True,
        robots_txt_content="User-agent: *\nAllow: /",
        broken_links=[],
        sitemap_urls=urls,
        target_max_pages=5,
        discovery_truncated=True,
        discovered_urls=[f"https://example.com/page-{i}" for i in range(504)],
    )
    assert manifest.ttfb_stats is not None
    assert manifest.ttfb_stats.median_ms == 288.0
    assert manifest.ttfb_stats.mean_ms == pytest.approx(7468.2, abs=0.1)
    assert manifest.ttfb_stats.outlier_urls == ["https://example.com/services"]
    assert manifest.crawl_health["median_ttfb_ms"] == 288.0
    assert manifest.crawl_health["max_ttfb_ms"] == 36208.0
    assert manifest.crawl_health["ttfb_outlier_urls"] == ["https://example.com/services"]
    assert manifest.url_coverage_pct == 1.0
    assert manifest.sampling_status == "SAMPLED_AUDIT"


def test_lighthouse_unmeasured_timing_does_not_fabricate_lcp_and_crux_aliases(monkeypatch):
    res = LighthouseRunner.evaluate_lighthouse_metrics(
        url="https://example.com/",
        ttfb_ms=250.0,
        dom_timing={"ttfb_ms": 250.0, "download_ms": 40.0},
    )
    assert res["lcp_ms"] is None
    assert "Not a Google Lighthouse run" in res["lighthouse_audit_version"]

    measured_res = LighthouseRunner.evaluate_lighthouse_metrics(
        url="https://example.com/",
        ttfb_ms=250.0,
        dom_timing={"ttfb_ms": 250.0, "fcp_ms": 820.0, "lcp_ms": 1450.0, "cls_score": 0.04},
    )
    assert measured_res["lcp_ms"] == 1450.0
    assert measured_res["cls_score"] == 0.04

    for alias in (
        "CRUX_API_KEY",
        "GOOGLE_CRUX_API_KEY",
        "PAGESPEED_API_KEY",
        "GOOGLE_PAGESPEED_API_KEY",
        "GOOGLE_API_KEY",
    ):
        for k in (
            "CRUX_API_KEY",
            "GOOGLE_CRUX_API_KEY",
            "PAGESPEED_API_KEY",
            "GOOGLE_PAGESPEED_API_KEY",
            "GOOGLE_API_KEY",
        ):
            monkeypatch.delenv(k, raising=False)
        monkeypatch.setenv(alias, f"key_from_{alias}")
        assert resolve_crux_api_key() == f"key_from_{alias}"


def test_evidence_to_url_reconciliation_across_all_pipeline_stages():
    # 1. Direct Finding model auto-backfill
    f_direct = Finding(
        finding_id="f_direct_1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing HSTS Header",
        evidence=[FindingEvidence(evidence_id="ev_1", url="https://example.com/a", value="missing")],
        affected_urls=[],
    )
    assert f_direct.affected_urls == ["https://example.com/a"]
    assert f_direct.affected_url_count == 1

    # 2. DecisionEngine
    class _DummyEvidenceStore:
        def get(self, ev_id):
            if ev_id == "ev_a":
                return SimpleNamespace(
                    id="ev_a",
                    url="https://example.com/a",
                    selector="h1",
                    value="Missing H1",
                    text="<h1> missing",
                )
            if ev_id == "ev_b":
                return SimpleNamespace(
                    id="ev_b",
                    url="https://example.com/b",
                    selector="h1",
                    value="Missing H1",
                    text="<h1> missing",
                )
            return None

        def get_observation(self, ev_id):
            return None

    claim = Claim(
        id="c_1",
        agent_id="seo_agent",
        statement="Page is missing an H1 heading",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        evidence_refs=["ev_a"],
        verification_status=VerificationStatus.VERIFIED,
    )
    engine = DecisionEngine()
    synthesized = engine.synthesize_findings([claim], _DummyEvidenceStore())
    assert len(synthesized) == 1
    assert synthesized[0].affected_urls == ["https://example.com/a"]
    assert synthesized[0].affected_url_count == 1

    # 3. FindingRegistry duplicate merge unions affected_urls & evidence_ids
    reg = FindingRegistry(run_id="run_test")
    f_reg_1 = Finding(
        finding_id="f_r1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Document lacks an H1 heading",
        evidence=[FindingEvidence(evidence_id="ev_a", url="https://example.com/a", element="h1", value="none")],
        affected_urls=[],
    )
    f_reg_2 = Finding(
        finding_id="f_r2",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        title="Missing H1 tag on service page",
        evidence=[FindingEvidence(evidence_id="ev_b", url="https://example.com/b", element="h1", value="none")],
        affected_urls=[],
    )
    reg.register(f_reg_1)
    entry, is_new = reg.register(f_reg_2)
    assert is_new is False
    assert entry.finding.affected_urls == ["https://example.com/a", "https://example.com/b"]
    assert entry.finding.affected_url_count == 2
    assert set(entry.finding.evidence_ids) == {"ev_a", "ev_b"}

    # 4. FindingDeduplicator preserves affected_urls and multi-discipline root-cause links
    f_dedup_seo = Finding(
        finding_id="f_d1",
        category=Category.SCHEMA,
        severity=Severity.MEDIUM,
        title="Organization schema missing on homepage",
        description="No JSON-LD structured data found.",
        why_it_matters="Search engines cannot verify organization entity.",
        evidence=[FindingEvidence(evidence_id="ev_s1", url="https://example.com/a", element="script[type='application/ld+json']", value="[]")],
        affected_urls=[],
    )
    f_dedup_geo = Finding(
        finding_id="f_d2",
        category=Category.GEO,
        severity=Severity.HIGH,
        title="Entity graph and sameAs structured data missing",
        description="Unlinked entity disambiguation in JSON-LD.",
        why_it_matters="AI answer engines cannot disambiguate brand identity.",
        evidence=[FindingEvidence(evidence_id="ev_s2", url="https://example.com/b", element="script[type='application/ld+json']", value="[]")],
        affected_urls=[],
    )
    deduped = FindingDeduplicator.deduplicate([f_dedup_seo, f_dedup_geo])
    assert len(deduped) == 1
    canon = deduped[0]
    assert canon.affected_urls == ["https://example.com/a", "https://example.com/b"]
    assert canon.affected_url_count == 2
    assert canon.root_cause_id.startswith("RC_")
    assert len(canon.linked_consequences) == 2

    rc_links = build_root_cause_links(deduped)
    assert len(rc_links) == 1
    assert rc_links[0].affected_urls == ["https://example.com/a", "https://example.com/b"]
    assert len(rc_links[0].discipline_consequences) >= 2


def test_consistency_engine_recomputes_issue_ledger_and_syncs_urls():
    # Setup report where Step 9 drops a contradicted finding (all pages have canonical_url)
    # and Step 11 adds F-ONPAGE-DUP-DESC from meta_rollup.duplicate_descriptions
    pages = [
        PageEvidence(
            url="https://example.com/a",
            status_code=200,
            canonical_url="https://example.com/a",
            meta_description="Same description everywhere",
            images_without_alt=2,
        ),
        PageEvidence(
            url="https://example.com/b",
            status_code=200,
            canonical_url="https://example.com/b",
            meta_description="Same description everywhere",
            images_without_alt=0,
        ),
    ]
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com/a",
        total_pages_discovered=504,
        total_pages_crawled=2,
        pages=pages,
        discovered_urls=["https://example.com/a", "https://example.com/b", "https://example.com/c"],
        untested_discovered_urls=["https://example.com/c"],
    )

    contradicted_finding = Finding(
        finding_id="f_false_canonical",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Pages have no rel=canonical tag",
        description="Missing a canonical tag.",
        evidence=[FindingEvidence(evidence_id="ev_c1", url="https://example.com/a", value="none")],
    )
    valid_finding = Finding(
        finding_id="f_valid_hsts",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        title="Missing Strict-Transport-Security (HSTS) Header",
        description="HSTS header is absent.",
        evidence=[FindingEvidence(evidence_id="ev_h1", url="https://example.com/a", value="missing")],
        affected_urls=[],
    )

    report = ExecutiveReport(
        report_id="rep_m1",
        analysis_id="run_m1",
        org_id="org_m1",
        website_url="https://example.com",
        domain="example.com",
        scores=OverallScoreResult(
            overall_score=80.0,
            grade="B",
            health_label="Good",
            category_scores={
                "TECHNICAL_SEO": CategoryScore(
                    category=Category.TECHNICAL_SEO,
                    score=80.0,
                    weight=1.0,
                    weighted_score=80.0,
                    status="MEASURED",
                )
            },
        ),
        story_summary="Example Corp scored 80.0/100.",
        what_site_gets_right=["Fast"],
        what_is_holding_it_back=["Headers"],
        primary_strategic_opportunity="Add HSTS",
        consultant_advice_what_to_ignore="None",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Good",
            search_engine_perspective="Good",
            ai_answer_engine_perspective="Good",
        ),
        findings=[contradicted_finding, valid_finding],
        crawl_manifest=manifest,
        page_reports=[PageReport(url="https://example.com/a"), PageReport(url="https://example.com/b")],
        meta_rollup=MetaBucketRollup(
            total_pages_evaluated=2,
            duplicate_descriptions=[
                MetaBucketItem(url="https://example.com/a", text="Same description everywhere"),
                MetaBucketItem(url="https://example.com/b", text="Same description everywhere"),
            ],
        ),
    )

    reconciled_report, consistency = CrossChapterConsistencyEngine.audit_and_reconcile(report)

    # Contradicted canonical finding removed, missing alt finding + duplicate meta desc finding added
    finding_ids = {f.finding_id for f in reconciled_report.findings}
    assert "f_false_canonical" not in finding_ids
    assert "f_valid_hsts" in finding_ids
    assert "find_missing_image_alt" in finding_ids
    assert "F-ONPAGE-DUP-DESC" in finding_ids

    # Every finding has reconciled affected_urls and affected_url_count
    for f in reconciled_report.findings:
        assert len(f.affected_urls) > 0
        assert f.affected_url_count == len(f.affected_urls)

    # Issue ledger must match final findings 100%
    ledger = reconciled_report.issue_ledger
    assert ledger is not None
    assert ledger["total_distinct_findings"] == len(reconciled_report.findings)
    assert sum(ledger["severity_breakdown"].values()) == len(reconciled_report.findings)

    # URL registry and root cause links populated
    assert reconciled_report.url_registry is not None
    assert reconciled_report.url_registry.discovered_total == 504
    assert reconciled_report.url_registry.tested_total == 2
    assert len(reconciled_report.root_cause_links) == len(reconciled_report.findings)


@pytest.mark.asyncio
async def test_performance_agent_uses_median_vs_outlier_and_attaches_urls():
    pages = [
        PageEvidence(url="https://example.com/", ttfb_ms=345.0),
        PageEvidence(url="https://example.com/about", ttfb_ms=252.0),
        PageEvidence(url="https://example.com/services", ttfb_ms=36208.0),
        PageEvidence(url="https://example.com/work", ttfb_ms=288.0),
        PageEvidence(url="https://example.com/contact", ttfb_ms=248.0),
    ]
    manifest = CrawlManifest(
        domain="example.com",
        base_url="https://example.com/",
        pages=pages,
        ttfb_stats=compute_ttfb_stats(pages),
    )
    bb = SimpleNamespace(
        crawl_manifest=manifest,
        pages=pages,
        findings=[],
        claim_registry=None,
        evidence_store=None,
    )
    agent = PerformanceAgent()
    res = await agent.run(bb)
    assert res["observations"]["median_ttfb_ms"] == 288.0
    assert res["observations"]["outlier_urls"] == ["https://example.com/services"]
    assert len(bb.findings) == 1
    f = bb.findings[0]
    assert f.affected_urls == ["https://example.com/services"]
    assert f.affected_url_count == 1
    assert len(f.evidence) == 1
    assert f.evidence[0].url == "https://example.com/services"
    assert "288" in f.description


def test_repository_preserves_affected_urls_count_and_root_cause_id(tmp_path):
    db_file = str(tmp_path / "test_m1_audit.db")
    repo = AuditRepository(db_path=db_file)
    f = Finding(
        finding_id="f_repo_1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing HSTS Header",
        description="HSTS not configured.",
        root_cause_id="RC_SECURITY_HEADERS",
        evidence=[
            FindingEvidence(evidence_id="ev_1", url="https://example.com/a", value="missing"),
            FindingEvidence(evidence_id="ev_2", url="https://example.com/b", value="missing"),
        ],
    )
    repo.persist_findings("run_m1_repo", [f])
    loaded = repo.get_persisted_findings("run_m1_repo")
    assert len(loaded) == 1
    assert loaded[0].Affected_urls if hasattr(loaded[0], "Affected_urls") else loaded[0].affected_urls == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert loaded[0].affected_url_count == 2
    assert loaded[0].root_cause_id == "RC_SECURITY_HEADERS"
