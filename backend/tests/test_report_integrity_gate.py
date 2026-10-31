from types import SimpleNamespace

import pytest

from app.report_integrity_gate import validate_final_report


def _finding(finding_id="f_1", title="Missing canonical URL", refs=None, category="TECHNICAL_SEO"):
    return SimpleNamespace(
        finding_id=finding_id,
        title=title,
        finding=title,
        category=category,
        evidence_refs=list(refs or []),
        evidence_ids=[],
        evidence_references=[],
        evidence=[],
        severity="HIGH",
        materiality="MAJOR",
        confidence_rubric="LIKELY",
        source_agreement=1,
    )


def _report(findings=None, evidence=None, score=82.0):
    return SimpleNamespace(
        analysis_id="run_123",
        report_id="report_123",
        findings=list(findings if findings is not None else [_finding(refs=["ev_1"])]),
        evidence_ledger=evidence if evidence is not None else {"ev_1": {"url": "https://example.com/"}},
        scores=SimpleNamespace(overall_score=score, category_scores={}),
        quality_gate_results={},
        certification_status="NOT_ASSESSED",
        withheld_sections=[],
    )


def _manifest(findings=None):
    return SimpleNamespace(
        analysis_id="run_123",
        report_id="report_123",
        findings=list(findings if findings is not None else [SimpleNamespace(finding_id="f_1")]),
    )


def test_final_report_integrity_gate_passes_for_linked_evidence():
    result = validate_final_report(_report(), _manifest())
    assert result["status"] == "PASS"
    assert result["certified"] is True
    assert result["finding_count"] == 1


def test_final_report_integrity_gate_discloses_findings_without_evidence():
    result = validate_final_report(
        _report(findings=[_finding(refs=[])]),
        _manifest(),
    )
    assert result["status"] == "PASS_WITH_EVIDENCE_GAPS"
    assert result["certified"] is False
    assert result["unsupported_finding_ids"] == ["f_1"]


def test_final_report_integrity_gate_rejects_dangling_evidence_reference():
    with pytest.raises(ValueError, match="dangling evidence references"):
        validate_final_report(_report(findings=[_finding(refs=["ev_missing"])]), _manifest())


def test_final_report_integrity_gate_rejects_duplicate_finding_ids():
    findings = [_finding("f_1", "Missing canonical URL", ["ev_1"]),
                _finding("f_1", "Missing robots rule", ["ev_1"])]
    with pytest.raises(ValueError, match="duplicate finding_id"):
        validate_final_report(_report(findings=findings), _manifest())


def test_final_report_integrity_gate_rejects_duplicate_root_cause_keys():
    findings = [_finding("f_1", "Missing canonical URL", ["ev_1"]),
                _finding("f_2", "Missing canonical URL", ["ev_1"])]
    with pytest.raises(ValueError, match="duplicate finding root-cause keys"):
        validate_final_report(_report(findings=findings), _manifest())


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -1, 101, True, None])
def test_final_report_integrity_gate_rejects_invalid_overall_score(score):
    with pytest.raises(ValueError, match="overall score"):
        validate_final_report(_report(score=score), _manifest())


def test_final_report_integrity_gate_rejects_manifest_finding_mismatch():
    with pytest.raises(ValueError, match="manifest finding pins"):
        validate_final_report(_report(), _manifest(findings=[]))


def test_final_report_integrity_gate_rejects_category_weight_sum_mismatch():
    report = _report()
    report.scores.category_scores = {
        "TECHNICAL_SEO": SimpleNamespace(score=80.0, status="MEASURED", weight=0.6, weighted_score=48.0),
        "CONTENT": SimpleNamespace(score=70.0, status="MEASURED", weight=0.3, weighted_score=21.0),
    }
    with pytest.raises(ValueError, match="measured category weights do not sum"):
        validate_final_report(report, _manifest())


def test_final_report_integrity_gate_rejects_weighted_score_mismatch():
    report = _report()
    report.scores.category_scores = {
        "TECHNICAL_SEO": SimpleNamespace(score=80.0, status="MEASURED", weight=1.0, weighted_score=70.0),
    }
    with pytest.raises(ValueError, match="does not reconcile"):
        validate_final_report(report, _manifest())


def test_final_report_integrity_gate_rejects_numeric_score_for_unmeasured_category():
    report = _report()
    report.scores.category_scores = {
        "TECHNICAL_SEO": SimpleNamespace(score=0.0, status="NOT_MEASURED", weight=0.0, weighted_score=0.0),
    }
    with pytest.raises(ValueError, match="NOT_MEASURED but has a numeric score"):
        validate_final_report(report, _manifest())


def test_deduplicator_and_repair_report_keep_weights_and_refs_valid_for_final_gate():
    from app.domain.enums import Category, Severity
    from app.domain.models import (
        BusinessProfile,
        CategoryScore,
        ExecutiveReport,
        Finding,
        FindingEvidence,
        OverallScoreResult,
        ThreeWayComparison,
    )
    from app.remediation.deduplicator import FindingDeduplicator
    from app.reports.validation_gate import ValidationGate

    ev_list = [
        FindingEvidence(
            evidence_id=f"EV-IMG-ALT-{i:02d}",
            url="https://example.com/",
            element="img",
            value=f"/img-{i}.png",
            snippet=f'<img src="/img-{i}.png">',
            expected_condition="Informative content image must declare a non-empty alt attribute",
        )
        for i in range(10)
    ]
    f1 = Finding(
        finding_id="f_alt_1",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="10 Image Asset(s) Missing Alternative Text",
        description="Images lack alt attributes.",
        recommendation="Add alt text.",
        evidence=ev_list[:6],
        evidence_refs=[ev.evidence_id for ev in ev_list[:6]],
    )
    f2 = Finding(
        finding_id="f_alt_2",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Images lack alt attribute on homepage",
        description="Missing alt attributes.",
        recommendation="Add alt text.",
        evidence=ev_list[4:],
        evidence_refs=[ev.evidence_id for ev in ev_list[4:]],
    )
    deduped = FindingDeduplicator.deduplicate([f1, f2])
    assert len(deduped) == 1
    assert len(deduped[0].evidence) == 8
    assert set(deduped[0].evidence_refs) == {ev.evidence_id for ev in deduped[0].evidence}

    report = ExecutiveReport(
        report_id="rep_1",
        analysis_id="run_1",
        website_url="https://example.com",
        domain="example.com",
        generated_at="now",
        business_profile=BusinessProfile(
            business_name="Example Corp",
            industry="SaaS",
            niche="Cloud",
            products=["Core"],
            services=["Support"],
            target_audience="Developers",
            geography="Global",
            business_model="B2B SaaS",
            value_proposition="Cloud infrastructure",
        ),
        scores=OverallScoreResult(
            overall_score=80.0,
            grade="B",
            health_label="Good",
            category_scores={
                "TECHNICAL_SEO": CategoryScore(
                    category=Category.TECHNICAL_SEO,
                    score=80.0,
                    weight=0.5,
                    weighted_score=40.0,
                    status="MEASURED",
                    summary="Good",
                ),
                "ON_PAGE_SEO": CategoryScore(
                    category=Category.ON_PAGE_SEO,
                    score=80.0,
                    weight=0.5,
                    weighted_score=40.0,
                    status="MEASURED",
                    summary="Good",
                ),
            },
        ),
        story_summary="Example Corp scored 80.0/100.",
        what_site_gets_right=["Clean structure"],
        what_is_holding_it_back=["Image alt text"],
        primary_strategic_opportunity="Fix image alt attributes.",
        consultant_advice_what_to_ignore="Ignore minor cosmetic issues.",
        three_way_comparison=ThreeWayComparison(
            human_visitor_perspective="Clear",
            search_engine_perspective="Indexed",
            ai_answer_engine_perspective="Grounded",
        ),
        findings=deduped,
        evidence_ledger={},
    )
    repaired, _ = ValidationGate.repair_report(report)
    manifest = SimpleNamespace(
        analysis_id="run_1",
        report_id="rep_1",
        findings=[SimpleNamespace(finding_id=f.finding_id) for f in repaired.findings],
    )
    res = validate_final_report(repaired, manifest)
    assert res["status"] == "PASS"



