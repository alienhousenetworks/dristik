from app.reporting.layered.specialist_reports import SpecialistReportBuilder
from app.reporting.layered.models import SpecialistDiscipline


def test_competitive_report_does_not_invent_competitors():
    builder = SpecialistReportBuilder()
    report = builder.build_specialist_report(
        discipline=SpecialistDiscipline.COMPETITIVE,
        domain="example.com",
        audit_id="test-001",
        score=None,
        findings=[],
        benchmarks=None,
        diagnostics=None,
    )
    assert report.benchmark_comparative_tables == []
    assert report.technical_diagnostics == {}
    assert report.action_matrix == []
    text = report.executive_diagnostic_summary.lower()
    assert "comp-a.com" not in text
    assert "comp-b.com" not in text
    assert "not measured" in text


def test_technical_report_does_not_invent_server_metrics():
    builder = SpecialistReportBuilder()
    report = builder.build_specialist_report(
        discipline=SpecialistDiscipline.TECH_INFRASTRUCTURE,
        domain="example.com",
        audit_id="test-002",
        score=None,
        findings=[],
        benchmarks=None,
        diagnostics=None,
    )
    assert report.benchmark_comparative_tables == []
    assert report.technical_diagnostics == {}
    assert report.action_matrix == []
    text = report.executive_diagnostic_summary.lower()
    assert "180ms" not in text
    assert "1.4mb" not in text
    assert "not measured" in text


def test_remediation_report_does_not_invent_fix_rates():
    builder = SpecialistReportBuilder()
    report = builder.build_specialist_report(
        discipline=SpecialistDiscipline.REMEDIATION_VERIFICATION,
        domain="example.com",
        audit_id="test-003",
        score=None,
        findings=[],
        benchmarks=None,
        diagnostics=None,
    )
    assert report.benchmark_comparative_tables == []
    assert report.technical_diagnostics == {}
    assert report.action_matrix == []
    text = report.executive_diagnostic_summary.lower()
    assert "82.5%" not in text
    assert "not measured" in text
