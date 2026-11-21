"""Heading observations attached to a finding must not block PDF publication."""
from app.domain.enums import Category, Severity
from app.domain.models import Finding, FindingEvidence
from app.reports.evidence_ledger import merge_finding_evidence
from app.reports.validation_gate import ValidationGate
from tests.test_phase0_publication_guard import _make_sample_report


def _heading_finding() -> Finding:
    evidence = FindingEvidence(
        evidence_id="EV-HDG-SKIP-abc12345",
        url="https://example.com/about",
        element="h2/h3",
        value="Subheadings (H2/H3) exist without an H1 parent.",
        snippet="Heading hierarchy violation on https://example.com/about",
        test_method="crawl_html_headings",
        source="crawl",
    )
    return Finding(
        finding_id="finding_heading_hierarchy_skips",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Document Outline & Heading Hierarchy Fragmentation",
        evidence=[evidence],
        evidence_ids=[evidence.evidence_id],
        evidence_refs=[evidence.evidence_id],
    )


def test_gate_accepts_heading_evidence_attached_to_the_finding():
    report = _make_sample_report(
        findings=[_heading_finding()],
        evidence_ledger={"EV_002": {"id": "EV_002", "url": "https://example.com/"}},
    )

    result = ValidationGate.evaluate_quality_gates(report)
    gate = result["gates"]["gate_02_evidence_reference_integrity"]

    assert gate["status"] == "PASS"
    assert gate["related_ids"] == []


def test_gate_still_blocks_a_citation_with_no_evidence():
    finding = _heading_finding()
    finding.evidence = []
    report = _make_sample_report(
        findings=[finding],
        evidence_ledger={"EV_002": {"id": "EV_002", "url": "https://example.com/"}},
    )

    result = ValidationGate.evaluate_quality_gates(report)
    gate = result["gates"]["gate_02_evidence_reference_integrity"]

    assert gate["status"] == "FAIL"
    assert "EV-HDG-SKIP-abc12345" in gate["related_ids"]


def test_merge_copies_finding_evidence_into_the_ledger():
    ledger = merge_finding_evidence({"EV_002": {"id": "EV_002"}}, [_heading_finding()])

    assert "EV-HDG-SKIP-abc12345" in ledger
    assert ledger["EV-HDG-SKIP-abc12345"]["url"] == "https://example.com/about"
    assert ledger["EV_002"]["id"] == "EV_002"
