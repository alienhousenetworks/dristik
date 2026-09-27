"""
Unit tests for Dristik first-class Evidence Taxonomy and Epistemic Hierarchy.
Verifies the 5 explicit evidence classes:
- OBSERVED (Directly measured: DOM, HTTP, AST, Headers, Screenshot, Accessibility tree, Schema)
- EXTERNALLY_VERIFIED (Confirmed through external source: Search, Directory, Profile, Registry, GSC, Analytics)
- MODEL_INFERRED (LLM interpretation of observed evidence)
- HYPOTHESIS (Potential issue requiring verification / Single-source unverified)
- RECOMMENDATION (Proposed remediation)
"""
import pytest
from app.domain.models import Finding, FindingEvidence
from app.domain.enums import (
    Category,
    Severity,
    EvidenceClass,
    EvidenceSubtype,
    SourceIntegrityLabel,
)
from app.evidence.taxonomy import (
    classify_finding,
    generate_evidence_taxonomy_report,
    TAXONOMY_SPEC,
)


def test_evidence_taxonomy_classes_and_subtypes():
    assert len(TAXONOMY_SPEC) == 5
    assert EvidenceClass.OBSERVED in TAXONOMY_SPEC
    assert EvidenceClass.EXTERNALLY_VERIFIED in TAXONOMY_SPEC
    assert EvidenceClass.MODEL_INFERRED in TAXONOMY_SPEC
    assert EvidenceClass.HYPOTHESIS in TAXONOMY_SPEC
    assert EvidenceClass.RECOMMENDATION in TAXONOMY_SPEC

    # Check observed subtypes include DOM, HTTP, AST, Headers, Screenshot, Accessibility tree, Schema
    obs_ids = [s["id"] for s in TAXONOMY_SPEC[EvidenceClass.OBSERVED]["subtypes"]]
    assert "DOM" in obs_ids
    assert "HTTP" in obs_ids
    assert "AST" in obs_ids
    assert "HEADERS" in obs_ids
    assert "SCREENSHOT" in obs_ids
    assert "ACCESSIBILITY_TREE" in obs_ids
    assert "SCHEMA" in obs_ids

    # Check externally verified subtypes include Search, Business directory, Company profile, Certificate registry, GSC, Analytics
    ext_ids = [s["id"] for s in TAXONOMY_SPEC[EvidenceClass.EXTERNALLY_VERIFIED]["subtypes"]]
    assert "SEARCH" in ext_ids
    assert "BUSINESS_DIRECTORY" in ext_ids
    assert "COMPANY_PROFILE" in ext_ids
    assert "CERTIFICATE_REGISTRY" in ext_ids
    assert "GSC" in ext_ids
    assert "ANALYTICS" in ext_ids


def test_classify_observed_dom_finding():
    finding = Finding(
        finding_id="find_dom_001",
        title="Homepage H1 does not communicate service category",
        description="Observed 'BEYOND IMAGINATION' instead of core service category.",
        category=Category.ON_PAGE_SEO,
        severity=Severity.HIGH,
        recommendation="Rewrite H1 to include AI workflow automation",
        evidence=[
            FindingEvidence(
                evidence_id="ev_001",
                selector="h1:nth-of-type(1)",
                value="BEYOND IMAGINATION",
            )
        ],
    )
    ev_class, ev_sub = classify_finding(finding)
    assert ev_class == EvidenceClass.OBSERVED
    assert ev_sub == "DOM"


def test_classify_observed_schema_finding():
    finding = Finding(
        finding_id="find_schema_001",
        title="Missing Service Schema Markup",
        description="JSON-LD script tag has no Service entity declared.",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
        recommendation="Inject Service schema.org structured data",
        evidence=[
            FindingEvidence(
                evidence_id="ev_002",
                selector="script[type='application/ld+json']",
            )
        ],
    )
    ev_class, ev_sub = classify_finding(finding)
    assert ev_class == EvidenceClass.OBSERVED
    assert ev_sub == "SCHEMA"


def test_classify_externally_verified_finding():
    finding = Finding(
        finding_id="find_ext_001",
        title="Verified Search Console Index Discrepancy",
        description="GSC API reports 4 pages unindexed while sitemap claims 10.",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        recommendation="Request indexing in Google Search Console",
        source_integrity_label=SourceIntegrityLabel.CORROBORATED,
        evidence=[
            FindingEvidence(
                evidence_id="ext_gsc_01",
                type="external_ground_truth",
                source="gsc_api",
            )
        ],
    )
    ev_class, ev_sub = classify_finding(finding)
    assert ev_class == EvidenceClass.EXTERNALLY_VERIFIED
    assert ev_sub == "GSC"


def test_classify_hypothesis_single_source():
    finding = Finding(
        finding_id="find_hyp_001",
        title="Potential TTFB Variance on Asia-Pacific CDNs",
        description="Single-source unverified measurement: latency spiked on Tokyo edge point.",
        category=Category.TECHNICAL_SEO,
        severity=Severity.MEDIUM,
        recommendation="Conduct continuous edge traceroute to corroborate",
        source_integrity_label=SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED,
    )
    ev_class, ev_sub = classify_finding(finding)
    assert ev_class == EvidenceClass.HYPOTHESIS
    assert ev_sub == "SINGLE_SOURCE_UNVERIFIED"


def test_classify_model_inferred_finding():
    finding = Finding(
        finding_id="find_inf_001",
        title="Hero value proposition lacks commercial resonance",
        description="Cognitive synthesis indicates copy appeals to technologists rather than enterprise buyers.",
        category=Category.CONTENT,
        severity=Severity.MEDIUM,
        recommendation="Pivot messaging to emphasize ROI and cost savings",
    )
    ev_class, ev_sub = classify_finding(finding)
    assert ev_class == EvidenceClass.MODEL_INFERRED
    assert ev_sub == "SEMANTIC_SYNTHESIS"


def test_generate_evidence_taxonomy_report():
    findings = [
        Finding(
            finding_id="f1",
            title="DOM H1 check",
            description="h1 test",
            category=Category.ON_PAGE_SEO,
            severity=Severity.LOW,
            recommendation="fix h1",
            evidence=[FindingEvidence(selector="h1", value="test")],
        ),
        Finding(
            finding_id="f2",
            title="GSC search verify",
            description="gsc console check",
            category=Category.TECHNICAL_SEO,
            severity=Severity.MEDIUM,
            recommendation="fix gsc",
            source_integrity_label=SourceIntegrityLabel.CORROBORATED,
            evidence=[FindingEvidence(evidence_id="ext_1", type="external_ground_truth")],
        ),
        Finding(
            finding_id="f3",
            title="Working hypothesis on crawl budget",
            description="Single-source unverified crawl anomaly",
            category=Category.TECHNICAL_SEO,
            severity=Severity.LOW,
            recommendation="re-test",
            source_integrity_label=SourceIntegrityLabel.SINGLE_SOURCE_UNVERIFIED,
        ),
        Finding(
            finding_id="f4",
            title="Market tone inference",
            description="Copy tone feels informal for B2B",
            category=Category.CONTENT,
            severity=Severity.LOW,
            recommendation="professionalize tone",
        ),
    ]

    report = generate_evidence_taxonomy_report(findings, {"ev_1": {}})
    assert report.total_evidence_nodes == 5
    assert report.class_counts[EvidenceClass.OBSERVED.value] == 1
    assert report.class_counts[EvidenceClass.EXTERNALLY_VERIFIED.value] == 1
    assert report.class_counts[EvidenceClass.HYPOTHESIS.value] == 1
    assert report.class_counts[EvidenceClass.MODEL_INFERRED.value] == 1
    assert report.epistemic_integrity_score == 50.0  # 2/4 findings are observed or verified
    assert len(report.classes_breakdown) == 5
