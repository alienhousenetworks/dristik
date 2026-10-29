import pytest
from app.domain.models import Finding, FindingEvidence, HeadingHierarchyRollup, CrawlManifest
from app.domain.enums import Category, Severity, FindingClassification
from app.cognition.contradiction_engine import contradiction_engine, ContradictionEngine
from app.reports.validation_gate import ValidationGate


def test_cross_category_heading_contradiction_detection():
    finding_missing = Finding(
        finding_id="f_h1_missing",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Document lacks a top-level <h1> heading",
        description="Page has no <h1> tag defined in HTML.",
        recommendation="Add an <h1> tag declaring primary topic.",
    )
    finding_multiple = Finding(
        finding_id="f_h1_multiple",
        category=Category.UX_CONVERSION,
        severity=Severity.MEDIUM,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Multiple <h1> tags compete for topical authority",
        description="Page has 3 distinct <h1> elements.",
        recommendation="Consolidate down to a single <h1> heading.",
        evidence_level="E4_FIRST_PARTY_DOM",
    )

    reports, reconciled = contradiction_engine.reconcile([finding_missing, finding_multiple])
    assert len(reports) == 1
    # The higher-evidence finding (finding_multiple with E4) overrides the other
    assert reports[0].detected_type in [Category.UX_CONVERSION.value, Category.ON_PAGE_SEO.value]


def test_reconcile_with_manifest_and_rollups():
    # When HeadingAnalyzer found 0 pages missing an H1
    rollup = HeadingHierarchyRollup(
        total_pages_evaluated=5,
        total_heading_issues=1,
        h1_health_score=90.0,
        missing_h1=[],  # 0 missing H1 pages
    )

    f_spurious_missing = Finding(
        finding_id="acc_h1_err",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Accessibility: Heading Order (WCAG_1_3_1)",
        description="Heading outline issues on https://example.com: Document lacks a top-level <h1> heading.",
        recommendation="Ensure a single <h1> declares document topic.",
    )

    f_valid_multiple = Finding(
        finding_id="seo_h1_mult",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        classification=FindingClassification.VERIFIED_DEFECT,
        title="Multiple <h1> tags detected",
        description="Page has multiple <h1> tags.",
        recommendation="Consolidate headings into sequential outline.",
    )

    reconciled, actions = contradiction_engine.reconcile_with_manifest_and_rollups(
        [f_spurious_missing, f_valid_multiple],
        heading_hierarchy=rollup
    )

    assert len(actions) == 1
    assert "Suppressed finding acc_h1_err" in actions[0]
    # Spurious finding marked held_from_executive
    assert reconciled[0].held_from_executive is True
    assert reconciled[1].held_from_executive is False
