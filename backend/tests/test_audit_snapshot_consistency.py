"""Tests guaranteeing that the Complete Master Audit Book and every standalone
section report (SEO, GEO, AEO, CRO, Crawl, Competitors) render from one immutable
execution snapshot with identical Run ID, timestamp, configuration, crawl scope,
and aligned composite/section scores.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.aeo.reporting.audit_book import render_aeo_audit_book
from app.cro.reporting import render_cro_audit_book
from app.domain.enums import Category, Severity
from app.domain.models import (
    BusinessProfile,
    CategoryScore,
    CrawlManifest,
    CroAuditReport,
    ExecutiveReport,
    Finding,
    GeoReadinessReport,
    OverallScoreResult,
    PageEvidence,
    ThreeWayComparison,
)
from app.geo.reporting.geo_audit_book import render_geo_audit_book
from app.reports.adaptive_audit_book import (
    build_publication_manifest,
    render_adaptive_audit_book_html,
)
from app.reports.section_exports import section_report_generator
from app.reports.snapshot_provenance import (
    format_audit_execution_metadata,
    parse_audit_datetime,
)
from app.seo.reporting.seo_audit_book import render_seo_audit_book
from app.seo.reporting.seo_book_renderer import build_seo_book_context


def _perforacare_snapshot_report() -> ExecutiveReport:
    """Realistic multi-discipline report mirroring the perforacare.com RUN_159FBC1F scenario."""
    pages = [
        PageEvidence(url="https://perforacare.com", status_code=200, title="Perfora Oral Care", h1=["Real People, Real Results"], word_count=420),
        PageEvidence(url="https://perforacare.com/products/granite-black-power-flosser-dream-white-toothpaste-150-gm", status_code=200, title="Power Flosser", h1=[], word_count=310),
        PageEvidence(url="https://perforacare.com/pages/contact-us", status_code=200, title="Contact Us", h1=[], word_count=180),
        PageEvidence(url="https://perforacare.com/products/flexiclean-manual-toothbrush", status_code=200, title="FlexiClean Toothbrush", h1=[], word_count=290),
        PageEvidence(url="https://perforacare.com/pages/about-us", status_code=200, title="About Perfora", h1=[], word_count=260),
    ]
    findings = [
        Finding(
            finding_id="find_004",
            category=Category.UX_CONVERSION,
            severity=Severity.MEDIUM,
            title="https://perforacare.com copy — cta: Only one observed CTA, a bundle offer",
            description="No primary add-to-cart or explore CTA observed above the fold.",
            evidence_id="ev_cro_001",
            recommendation="Add primary Add to Cart and Explore CTAs.",
            affected_urls=["https://perforacare.com"],
        ),
    ]
    for idx in range(1, 19):
        findings.append(
            Finding(
                finding_id=f"find_seo_{idx:03d}",
                category=Category.TECHNICAL_SEO if idx <= 12 else Category.GEO,
                severity=Severity.HIGH if idx <= 6 else Severity.MEDIUM,
                title=f"Technical or GEO observation #{idx}",
                description=f"Observed deterministic defect #{idx} across sampled pages.",
                evidence_id=f"ev_{idx:03d}",
                recommendation=f"Remediate defect #{idx}.",
                affected_urls=[pages[idx % len(pages)].url],
            )
        )

    return ExecutiveReport(
        org_id="org_perfora",
        report_id="rep_159fbc1f0001",
        analysis_id="run_159fbc1f9988",
        website_url="https://perforacare.com",
        domain="perforacare.com",
        generated_at="November 22, 2026 - 05:24 UTC",
        policy_pack="enterprise_web_intel_v4",
        target_pillars=["seo", "geo", "aeo", "cro"],
        business_profile=BusinessProfile(business_name="Perfora"),
        crawl_manifest=CrawlManifest(
            domain="perforacare.com",
            total_pages_discovered=503,
            pages=pages,
        ),
        scores=OverallScoreResult(
            overall_score=45.8,
            grade="F",
            health_label="Critical",
            category_scores={
                "TECHNICAL_SEO": CategoryScore(category=Category.TECHNICAL_SEO, score=44.0),
                "GEO": CategoryScore(category=Category.GEO, score=65.0),
                "SCHEMA": CategoryScore(category=Category.SCHEMA, score=41.0),
                "UX_CONVERSION": CategoryScore(category=Category.UX_CONVERSION, score=50.0),
            },
            website_geo_readiness_score=65.0,
            aeo_readiness_score=41.0,
            cro_score=50.0,
        ),
        geo_readiness=GeoReadinessReport(
            extractability_score=65.0,
            schema_crosscheck={"quality_score": 41.0},
        ),
        cro_audit=CroAuditReport(overall_cro_score=50.0),
        story_summary="Multi-discipline diagnostic summary for Perfora.",
        primary_strategic_opportunity="Resolve H1 hierarchy and primary CTA clarity.",
        consultant_advice_what_to_ignore="Defer cosmetic animations until core defects are closed.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Only a bundle CTA is visible above the fold.",
            search_engine_perspective="Four sampled pages lack an H1 element.",
            ai_answer_engine_perspective="Brand category and pricing facts are missing from DOM.",
        ),
        findings=findings,
    )


def test_parse_audit_datetime_never_truncates_november_22_to_november_2():
    date_part, ts_part = parse_audit_datetime("November 22, 2026 - 05:24 UTC")
    assert date_part == "November 22, 2026"
    assert ts_part == "November 22, 2026 · 05:24 UTC"
    assert date_part != "November 2"

    iso_date, iso_ts = parse_audit_datetime("2026-11-22T05:24:00Z")
    assert iso_date == "November 22, 2026"
    assert iso_ts == "November 22, 2026 · 05:24 UTC"

    nov_18_date, _ = parse_audit_datetime("November 18, 2026 - 11:00 UTC")
    assert nov_18_date == "November 18, 2026"
    assert nov_18_date != "November 1"

    single_day, _ = parse_audit_datetime("November 02, 2026 - 05:24 UTC")
    assert single_day == "November 2, 2026"


def test_master_book_and_all_standalone_reports_share_one_immutable_snapshot():
    report = _perforacare_snapshot_report()
    snap = format_audit_execution_metadata(report)

    assert snap.report_ref == "RUN_159FBC1F"
    assert snap.execution_date == "November 22, 2026"
    assert snap.execution_timestamp == "November 22, 2026 · 05:24 UTC"
    assert snap.crawl_scope_summary == "5 URLs inspected of 503 discovered"
    assert snap.composite_score == 45.8
    assert snap.total_findings_count == 19
    assert snap.score_for_section("seo") == 44.0
    assert snap.score_for_section("geo") == 65.0
    assert snap.score_for_section("aeo") == 41.0
    assert snap.score_for_section("cro") == 50.0
    assert snap.findings_for_section("cro") == 1

    # Render Master Book and every standalone report from the same snapshot
    master_html = render_adaptive_audit_book_html(report, report_type="COMPLETE")
    seo_html = render_seo_audit_book(report)
    geo_html = render_geo_audit_book(report)
    aeo_html = render_aeo_audit_book(report)
    cro_html = render_cro_audit_book(report)
    crawl_section_html = section_report_generator.render_section_html(report, "crawl")
    comp_section_html = section_report_generator.render_section_html(report, "competitors")

    outputs = {
        "master": master_html,
        "seo": seo_html,
        "geo": geo_html,
        "aeo": aeo_html,
        "cro": cro_html,
        "crawl": crawl_section_html,
        "competitors": comp_section_html,
    }

    for name, doc in outputs.items():
        # Exact same Run ID, Snapshot ID, Timestamp, Configuration, Crawl Scope, Composite Score, and Section Scores
        assert "RUN_159FBC1F" in doc, f"{name} missing RUN_159FBC1F"
        assert snap.snapshot_id in doc, f"{name} missing snapshot_id {snap.snapshot_id}"
        assert "November 22, 2026" in doc, f"{name} missing full execution date"
        assert "November 22, 2026 · 05:24 UTC" in doc, f"{name} missing full execution timestamp"
        assert ">November 2<" not in doc, f"{name} truncated November 22 to November 2"
        assert "5 URLs inspected of 503 discovered" in doc, f"{name} missing unified crawl scope"
        assert "enterprise_web_intel_v4" in doc, f"{name} missing configuration policy pack"
        assert "45.8 / 100" in doc, f"{name} missing composite score 45.8 / 100"
        assert "19 total execution findings" in doc, f"{name} missing total findings count context"
        assert "SEO 44.0 · GEO 65.0 · AEO 41.0 · CRO 50.0" in doc, f"{name} missing aligned section score strip"

    # Master Book Chapter 00 5-pillar table renders exact section scores (not None / —)
    assert "44.0" in master_html
    assert "65.0" in master_html
    assert "41.0" in master_html
    assert "50.0" in master_html

    # SEO book renderer context also carries full non-truncated date and run ref
    seo_ctx = build_seo_book_context(report)
    seo_rep_ctx = seo_ctx.get("report", seo_ctx)
    assert seo_rep_ctx["run_id"] == "RUN_159FBC1F"
    assert seo_rep_ctx["audit_date"] == "November 22, 2026 · 05:24 UTC"

    # Publication manifest carries full non-truncated date and snapshot metadata
    manifest = build_publication_manifest(report, "COMPLETE")
    assert manifest["audit_date"] == "November 22, 2026"
    assert manifest["execution_timestamp"] == "November 22, 2026 · 05:24 UTC"
    assert manifest["report_ref"] == "RUN_159FBC1F"
    assert manifest["snapshot_id"] == snap.snapshot_id


def test_strict_snapshot_isolation_blocks_unlinked_geo_store_drift(monkeypatch):
    from app.geo.reporting.builder import load_latest_enterprise_geo_dataset

    report = _perforacare_snapshot_report()
    object.__setattr__(report, "_strict_snapshot_isolation", True)

    fake_other_audit = SimpleNamespace(
        audit_id="geo_unrelated_newer_run",
        parent_run_id="run_DIFFERENT",
        domain="perforacare.com",
        website_url="https://perforacare.com",
    )

    class _FakeStore:
        def list_audits(self, tenant_id, limit=50):
            return [fake_other_audit]

    result = load_latest_enterprise_geo_dataset(report, store=_FakeStore())
    assert result is None
