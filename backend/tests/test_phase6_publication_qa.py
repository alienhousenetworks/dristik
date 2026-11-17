import pytest
from app.domain.models import ExecutiveReport, OverallScoreResult, Finding, FindingEvidence, CroAuditReport
from app.domain.enums import PublicationStatus, Category, Severity
from app.reports.validation_gate import ReportPublicationValidator

def _make_base_report(**kwargs):
    defaults = {
        "org_id": "test_org",
        "report_id": "RUN_AF865F8B",
        "analysis_id": "RUN_AF865F8B",
        "website_url": "https://perforacare.com",
        "domain": "perforacare.com",
        "scores": OverallScoreResult(overall_score=75.2, grade="B", health_label="Good"),
        "story_summary": "Test story summary.",
        "primary_strategic_opportunity": "Test strategic opportunity.",
        "consultant_advice_what_to_ignore": "Test advice.",
        "findings": [
            Finding(
                finding_id="F_01",
                title="Missing Alt",
                category=Category.ON_PAGE_SEO,
                severity=Severity.LOW,
                evidence=[FindingEvidence(url="https://perforacare.com", selector="img", text="alt")],
            )
        ],
        "certification_status": "NOT_ASSESSED",
    }
    defaults.update(kwargs)
    return ExecutiveReport(**defaults)

def test_phase6_publication_validator_catches_run_id_mismatch():
    """Verify publication validator blocks if deliverable manifests have mismatched run IDs."""
    report = _make_base_report()
    deliverables = {
        "seo_report": {"report_id": "RUN_AF865F8B", "score": 75.2},
        "master_book": {"report_id": "RUN_DIFFERENT_99", "score": 75.2}, # Contradiction!
    }
    qa = ReportPublicationValidator.validate_publication_bundle(report, deliverables)
    assert qa.is_publishable is False
    assert qa.status == PublicationStatus.BLOCKED
    assert any("mismatched run_id" in r for r in qa.blocking_reasons)

def test_phase6_publication_validator_catches_score_mismatch():
    """Verify publication validator blocks if deliverable manifests have conflicting scores."""
    report = _make_base_report()
    deliverables = {
        "seo_report": {"report_id": "RUN_AF865F8B", "score": 75.2},
        "exec_deck": {"report_id": "RUN_AF865F8B", "score": 88.0}, # Contradictory score!
    }
    qa = ReportPublicationValidator.validate_publication_bundle(report, deliverables)
    assert qa.is_publishable is False
    assert qa.status == PublicationStatus.BLOCKED
    assert any("conflicting overall score" in r for r in qa.blocking_reasons)

def test_phase6_publication_validator_blocks_cro_false_certification():
    """Verify publication validator blocks if CRO is certified while interaction tests are unmeasured."""
    report = _make_base_report(
        cro_audit=CroAuditReport(),
        certification_status="CERTIFIED", # Unjustified certified status!
    )
    qa = ReportPublicationValidator.validate_publication_bundle(report)
    assert qa.is_publishable is False
    assert qa.status == PublicationStatus.BLOCKED
    assert any("CRO forms and browser interaction tests are unmeasured" in r for r in qa.blocking_reasons)

def test_phase6_valid_bundle_passes():
    """Verify clean, reconciled bundle passes QA and is ready for publication."""
    report = _make_base_report(
        certification_status="PUBLISHED_WITH_LIMITATIONS",
    )
    deliverables = {
        "seo_report": {"report_id": "RUN_AF865F8B", "score": 75.2},
        "geo_report": {"report_id": "RUN_AF865F8B", "score": 75.2},
        "master_book": {"report_id": "RUN_AF865F8B", "score": 75.2},
    }
    qa = ReportPublicationValidator.validate_publication_bundle(report, deliverables)
    assert qa.is_publishable is True
    assert len(qa.blocking_reasons) == 0
