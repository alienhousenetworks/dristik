import pytest
from app.seo.audit.qa.seo_qa_validator import SeoQaValidator

def test_seo_qa_validator_pass():
    validator = SeoQaValidator()

    assessment = type("MockAssessment", (), {
        "findings": [
            {
                "finding_id": "SEO_FND_01",
                "severity": "CRITICAL",
                "evidence_refs": ["SEO_EV_01"],
                "verification_status": "VERIFIED_FIXED",
                "remediation_verification": {"passed": True},
            }
        ],
        "evidence": [{"evidence_id": "SEO_EV_01", "element": "head.canonical"}],
        "coverage": {"urls_crawled": 5},
    })()

    report_data = {
        "analysis_id": "TEST_RUN_001",
        "scores": {"overall_score": 78, "category_scores": {"TECHNICAL_SEO": 78}},
        "crawl_manifest": {"pages": [{"url": "https://example.com/"}] * 5},
    }

    report = validator.validate(assessment, report_data)
    assert report.is_certified is True
    assert report.status == "CERTIFIED"
    assert report.blockers_count == 0

def test_seo_qa_validator_fail_closed_on_unsupported_finding():
    validator = SeoQaValidator()

    # Finding has no evidence and no evidence_refs
    assessment = type("MockAssessment", (), {
        "findings": [
            {
                "finding_id": "SEO_HALLUCINATED_01",
                "severity": "CRITICAL",
                "evidence": [],
                "evidence_refs": [],
                "verification_status": "VERIFIED",
            }
        ],
        "evidence": [],
    })()

    report_data = {
        "analysis_id": "TEST_RUN_002",
        "scores": {"overall_score": 50},
    }

    report = validator.validate(assessment, report_data)
    assert report.is_certified is False
    assert report.status == "BLOCKED_INTEGRITY_FAILURE"
    assert report.blockers_count >= 1
    assert any("lack empirical evidence" in r for r in report.blocking_reasons)
