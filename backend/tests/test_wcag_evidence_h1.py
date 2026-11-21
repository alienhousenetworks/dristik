"""Pages with no parsed h1 must use crawl evidence and must not crash the auditor."""
from app.cro.accessibility.wcag_auditor import DeepWcagAuditor
from app.domain.models import PageEvidence


def test_audit_pages_uses_evidence_h1_when_html_has_none():
    html = "<html><head><title>Home</title></head><body><p>No heading tag here.</p></body></html>"
    pages = [
        PageEvidence(
            url="https://example.com/",
            title="Home",
            raw_html=html,
            h1=["Measured evidence heading"],
        )
    ]

    summary, findings = DeepWcagAuditor.audit_pages(pages)

    heading_violations = [v for v in summary.violations if v.rule_id == "WCAG_1_3_1_HEADING_ORDER"]
    assert heading_violations == []
    assert all(getattr(f, "rule_id", None) != "WCAG_1_3_1_HEADING_ORDER" for f in findings)


def test_audit_pages_reports_missing_h1_without_raising():
    html = "<html><head><title>Home</title></head><body><p>No heading tag here.</p></body></html>"
    pages = [PageEvidence(url="https://example.com/empty", title="Home", raw_html=html, h1=[])]

    summary, _findings = DeepWcagAuditor.audit_pages(pages)

    assert any(v.rule_id == "WCAG_1_3_1_HEADING_ORDER" for v in summary.violations)
