"""Phase 2 Gate: Canonical Finding Object, Single Severity/Effort, Connector Verdicts & Banner Guards."""
from __future__ import annotations

from types import SimpleNamespace

from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.report_finding_registry import (
    chapter_has_defects,
    compute_canonical_effort,
    compute_canonical_severity,
    normalize_canonical_findings,
    partition_findings_for_chapter,
    resolve_connector_verdict,
    resolve_owning_chapter,
)
from app.reports.plain_english_engine import SectionBusinessExplanation, render_section_business_callout


def test_canonical_finding_fields_and_single_owner():
    f_ttfb = Finding(
        finding_id="FND_TTFB",
        rule_id="TTFB_P1",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Slow TTFB on homepage (2809ms)",
        effort=3,
        evidence_ids=["EV_001"],
    )
    f_title = Finding(
        finding_id="FND_TITLE",
        rule_id="TITLE_LENGTH_001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Product page title is 'kwikpass'",
        effort=2,
        evidence_ids=["EV_021"],
    )
    f_pass = {
        "finding_id": "find_001",
        "title": "PASS: Robots.txt reachable",
        "status": "PASS",
        "severity": "INFO",
    }

    report = SimpleNamespace(findings=[f_ttfb, f_title, f_pass])
    canonical = normalize_canonical_findings(report, active_connectors=set())

    # Passes are stripped from findings[]
    assert len(canonical) == 2
    assert all(getattr(f, "finding_id", "") != "find_001" for f in canonical)

    # Single owning chapter + cross-ref partitioning
    crawl_owned, crawl_xrefs = partition_findings_for_chapter(canonical, "crawl")
    seo_owned, seo_xrefs = partition_findings_for_chapter(canonical, "seo")
    assert [f.finding_id for f in crawl_owned] == ["FND_TTFB"]
    assert [f.finding_id for f in crawl_xrefs] == ["FND_TITLE"]
    assert [f.finding_id for f in seo_owned] == ["FND_TITLE"]
    assert [f.finding_id for f in seo_xrefs] == ["FND_TTFB"]

    # Single severity, effort, algo_trace, and connector verdict
    assert compute_canonical_severity(f_ttfb) == "HIGH"
    assert compute_canonical_effort(f_ttfb) == "Low"
    assert f_ttfb.algo_trace and f_ttfb.algo_trace[0]["rule_id"] == "TTFB_P1"
    assert f_ttfb.connector_effect["needs_connector"] == "PageSpeed/CrUX"
    assert f_title.connector_effect["resolves_issue"] == "PARTIAL"
    assert f_title.connector_effect["needs_connector"] == "Search Console"


def test_connector_off_verdict_never_confirms_unmeasured_impact():
    geo_finding = {"finding_id": "F1", "category": "GEO", "title": "Schema missing Product offers"}
    verdict_off = resolve_connector_verdict(geo_finding, active_connectors=set())
    assert verdict_off["resolves_issue"] == "CANNOT CONFIRM"
    assert verdict_off["needs_connector"] == "Live AI/AEO"

    verdict_on = resolve_connector_verdict(geo_finding, active_connectors={"Live AI/AEO"})
    assert verdict_on["resolves_issue"] == "YES"
    assert verdict_on["needs_connector"] is None


def test_no_defects_banner_cannot_contradict_owned_findings():
    assert chapter_has_defects([{"finding_id": "F1"}]) is True
    assert chapter_has_defects([]) is False

    exp = SectionBusinessExplanation(
        section_id="seo",
        section_title="SEO",
        plain_english_subject="SEO checks",
        key_result="1 defect found",
        why_reader_should_care="Impacts rankings",
        recommended_action="Fix title",
        evidence_status="SAMPLE_TESTED_CLEAN",  # even if mistakenly passed clean
        evidence_status_note="Sampled",
        sample_size=5,
        pages_affected=2,  # contradicts clean!
    )
    html = render_section_business_callout(exp)
    assert "NO DEFECTS RECORDED" not in html
    assert "ISSUES REQUIRING ATTENTION" in html
