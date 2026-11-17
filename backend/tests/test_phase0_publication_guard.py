import pytest
from app.core.config import settings
from app.domain.enums import PublicationStatus, Category, Severity
from app.domain.models import ExecutiveReport, CroAuditReport, OverallScoreResult, Finding
from app.reports.validation_gate import ValidationGate

def _make_sample_report(**kwargs):
    defaults = {
        "org_id": "test_org",
        "report_id": "DST-TEST-001",
        "analysis_id": "test-run-123",
        "website_url": "https://example.com",
        "domain": "example.com",
        "generated_at": "2026-10-15T12:00:00Z",
        "scores": OverallScoreResult(overall_score=78.5, grade="B+", health_label="Good"),
        "story_summary": "Robust infrastructure with isolated crawl directive blockers.",
        "primary_strategic_opportunity": "Unlock catalog search indexing.",
        "consultant_advice_what_to_ignore": "Ignore minor meta keywords tags.",
        "what_site_gets_right": ["SSL active"],
        "what_is_holding_it_back": ["Schema gap"],
    }
    defaults.update(kwargs)
    return ExecutiveReport(**defaults)

def test_phase0_feature_flag_and_enums():
    """Verify REPORT_PUBLICATION_GUARD exists and PublicationStatus enum is defined."""
    assert hasattr(settings, "REPORT_PUBLICATION_GUARD")
    assert PublicationStatus.DRAFT == "DRAFT"
    assert PublicationStatus.INTERNAL_REVIEW == "INTERNAL_REVIEW"
    assert PublicationStatus.BLOCKED == "BLOCKED"
    assert PublicationStatus.READY_FOR_PUBLICATION == "READY_FOR_PUBLICATION"
    assert PublicationStatus.PUBLISHED == "PUBLISHED"

def test_phase0_blocked_on_unmeasured_cro_and_gate_failure():
    """Verify that unmeasured CRO interactions prevent CERTIFIED and trigger INTERNAL_REVIEW/BLOCKED with reasons."""
    report = _make_sample_report(
        certification_status="NOT_ASSESSED",
        cro_audit=CroAuditReport(), # Unmeasured forms and browser UX
    )
    repaired, result = ValidationGate.enforce_gate(report)
    assert repaired.certification_status != "CERTIFIED"
    assert repaired.publication_status in (PublicationStatus.BLOCKED, PublicationStatus.INTERNAL_REVIEW)
    assert len(repaired.publication_blocking_reasons) > 0

def test_phase0_historical_reports_preserve_status():
    """Historical reports maintain explicit publication status and original run identifiers."""
    report = _make_sample_report(
        report_id="RUN_HISTORICAL_123",
        publication_status=PublicationStatus.PUBLISHED,
        certification_status="CERTIFIED"
    )
    assert report.report_id == "RUN_HISTORICAL_123"
    assert report.publication_status == PublicationStatus.PUBLISHED
