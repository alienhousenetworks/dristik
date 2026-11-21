"""CRO PDF publication: one data source, honest statuses, blocking gate, no stub PDFs."""
import asyncio
from types import SimpleNamespace

import pytest

from app.cro.engine import build_from_executive_report
from app.cro.quality import cro_publication_gate
from app.cro.reporting import build_cro_publication_document, compute_cro_status, render_cro_audit_book
from app.domain.models import PageEvidence


def _report(ctas=("Explore Oral Care",)):
    p = PageEvidence(url="https://example.com/", title="Store", h1=["Oral care that lasts"], word_count=300, ctas=list(ctas))
    return SimpleNamespace(
        domain="example.com", website_url="https://example.com", generated_at="2026-11-22T10:00:00Z",
        analysis_id="cro_pdf_001", crawl_manifest=SimpleNamespace(pages=[p], total_pages_discovered=5),
        scores=None, contradictions=[], policy_pack="cro_audit",
    )


def test_document_uses_cro_engine_and_discloses_scope():
    report = _report()
    intel = build_from_executive_report(report)
    doc = build_cro_publication_document(report, intel)
    ids = [c.id for p in doc.parts for c in p.chapters]
    assert ids[0] == "cro_exec" and "cro_scope" in ids
    assert doc.metadata.findings_count == len(intel.findings)
    html = render_cro_audit_book(report)
    assert "NOT MEASURED" in html or "Unmeasured" in html or "DATA_UNAVAILABLE" in html
    assert compute_cro_status(intel)["certification_status"] == "NOT_CERTIFIED"


def test_gate_blocks_contradictions_and_unreproducible_scores():
    intel = build_from_executive_report(_report())
    assert cro_publication_gate(intel).passed or cro_publication_gate(intel).reasons  # runs on real data
    exp = next(d for d in intel.dimensions if d.id == "experience")
    exp.score, exp.passed_checks, exp.failed_checks = 99.0, 1, 1
    assert any("not reproducible" in r for r in cro_publication_gate(intel).reasons)

    intel.metrics[0].status, intel.metrics[0].value = "DATA_UNAVAILABLE", 0.0
    assert any("has a value but status" in r for r in cro_publication_gate(intel).reasons)


def test_gate_flags_cta_reported_missing_while_cta_evidence_exists():
    intel = build_from_executive_report(_report())
    check = intel.sections[0].checks[0]
    check.key, check.outcome, check.evidence = "primary_cta", "pass", ["page:https://example.com/#cta"]
    if intel.findings:
        intel.findings[0].finding = "No CTA was found on the inspected pages."
    else:
        pytest.skip("engine produced no finding to contradict")
    assert any("CTA reported missing" in r for r in cro_publication_gate(intel).reasons)


def test_failed_pdf_qa_blocks_publication():
    intel = build_from_executive_report(_report())
    qa = SimpleNamespace(is_valid=False, failed_checks=["check_toc_page_numbers"])
    assert any("PDF QA failed" in r for r in cro_publication_gate(intel, qa).reasons)


def test_pdf_renders_when_browser_available():
    from app.reports.publishing_engine import PdfPublishingPipeline
    report = _report()
    doc = build_cro_publication_document(report)
    pdf, qa = asyncio.run(PdfPublishingPipeline.render_publication_pdf(doc))
    if not pdf:
        pytest.skip("headless Chromium unavailable")
    assert pdf.startswith(b"%PDF-")
    assert cro_publication_gate(build_from_executive_report(report), qa).passed, qa.failed_checks


def test_all_findings_and_old_findings_included_in_pdf():
    """Verify that every finding from report.findings (including non-UX/CRO categories) is preserved in PDF."""
    from app.domain.enums import Category, Severity
    from app.domain.models import Finding
    from app.reports.publishing_engine import PublicationHtmlRenderer

    base_rep = _report()
    test_findings = [
        Finding(
            finding_id="F-SEO-01",
            category=Category.TECHNICAL_SEO,
            title="Sitemap index missing essential product categories",
            description="XML sitemap excludes several top-level routes.",
            severity=Severity.HIGH,
            recommendation="Add missing product XML sitemaps to robots.txt and sitemap index.",
        ),
        Finding(
            finding_id="F-MOBILE-01",
            category=Category.UX_CONVERSION,
            title="Mobile tap targets under 48px in header navigation",
            description="Navigation touch elements overlap on mobile viewport.",
            severity=Severity.MEDIUM,
            recommendation="Increase touch target padding to minimum 48x48 CSS pixels.",
        ),
        Finding(
            finding_id="F-EXT-01",
            category=Category.EXTERNAL_AUTHORITY,
            title="Broken inbound backlinks pointing to legacy 404 URLs",
            description="External referring domains link to deleted product pages.",
            severity=Severity.LOW,
            recommendation="Implement permanent 301 redirects to active category pages.",
        ),
        Finding(
            finding_id="F-WCAG-01",
            category=Category.CONTENT,
            title="Form controls missing aria-label attributes",
            description="Screen readers cannot resolve input purposes.",
            severity=Severity.HIGH,
            recommendation="Add aria-label or visible label elements to all inputs.",
        ),
    ]
    base_rep.findings = test_findings

    intel = build_from_executive_report(base_rep)
    finding_titles = [f.finding for f in intel.findings]
    assert any("Sitemap index" in t for t in finding_titles)
    assert any("Mobile tap targets" in t for t in finding_titles)
    assert any("Broken inbound backlinks" in t for t in finding_titles)
    assert any("Form controls missing" in t for t in finding_titles)

    doc = build_cro_publication_document(base_rep, intel)
    rendered_html = PublicationHtmlRenderer.render(doc)

    for f in test_findings:
        assert f.finding_id in rendered_html
        assert f.title in rendered_html
        assert f.recommendation in rendered_html

    from app.reports.adaptive_audit_book import render_adaptive_audit_book_html
    adaptive_html = render_adaptive_audit_book_html(base_rep, report_type="CRO")
    for f in test_findings:
        assert f.finding_id in adaptive_html
        assert f.title in adaptive_html
