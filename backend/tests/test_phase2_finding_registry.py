import pytest
from app.domain.models import AuditFinding, Finding, FindingEvidence
from app.domain.enums import Category, Severity, FindingStatus
from app.remediation.deduplicator import FindingDeduplicator

def test_phase2_audit_finding_model():
    """Verify standard AuditFinding model and its conversion to domain Finding."""
    af = AuditFinding(
        id="FINDING_TTFB_001",
        audit_run_id="RUN_AF865F8B",
        discipline="SEO",
        category="TECHNICAL_SEO",
        title="Isolated TTFB Latency Outlier on Unwind Product Page",
        description="The /products/unwind page recorded 36,208ms TTFB while the other 4 URLs averaged 284ms.",
        severity="HIGH",
        confidence="HIGH",
        evidence_status="OBSERVED",
        verification_status="OBSERVED",
        affected_urls=["https://perforacare.com/products/unwind"],
        evidence_ids=["ev_001", "ev_002"],
        root_cause="Database cold-query execution on combo product endpoint",
        business_impact="Excessive TTFB stalls crawler discovery and induces bounce rates on paid traffic.",
        impact_basis="INFERRED",
        recommended_fix="Precompute and cache SSR responses on edge CDN.",
        owner="Engineering",
        estimated_effort="MEDIUM",
        acceptance_criteria=["TTFB <= 600ms on subsequent crawl"],
    )
    assert af.id == "FINDING_TTFB_001"
    assert af.audit_run_id == "RUN_AF865F8B"
    assert af.affected_urls == ["https://perforacare.com/products/unwind"]
    assert len(af.evidence_ids) == 2

    # Conversion to Finding
    f = af.to_finding()
    assert f.finding_id == af.id
    assert f.category == Category.TECHNICAL_SEO
    assert f.severity == Severity.HIGH
    assert f.root_cause_id == af.root_cause
    assert f.recommendation == af.recommended_fix

def test_phase2_root_cause_deduplication():
    """Verify deduplicator clusters symptom findings into 1 root cause without double-counting."""
    f1 = Finding(
        finding_id="F1",
        title="Missing image alt text on homepage hero",
        description="Images lack alt attribute on /",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        affected_urls=["https://example.com/"],
        evidence=[FindingEvidence(url="https://example.com/", selector="img.hero", text="missing alt")],
    )
    f2 = Finding(
        finding_id="F2",
        title="Missing alt attribute on product thumbnails",
        description="Missing alt attribute on /products/teeth-whitening",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        affected_urls=["https://example.com/products/teeth-whitening"],
        evidence=[FindingEvidence(url="https://example.com/products/teeth-whitening", selector="img.thumb", text="missing alt")],
    )

    deduped = FindingDeduplicator.deduplicate([f1, f2])
    # Clustered into 1 canonical root cause finding
    assert len(deduped) == 1
    root = deduped[0]
    assert "RC_IMAGE_ACCESSIBILITY" in root.finding_id
    assert len(root.affected_urls) == 2
    assert "https://example.com/" in root.affected_urls
    assert "https://example.com/products/teeth-whitening" in root.affected_urls

def test_phase2_finding_states_lifecycle():
    """Verify lifecycle states from OBSERVED to VERIFIED_FIXED."""
    states = [
        FindingStatus.OBSERVED,
        FindingStatus.REMEDIATION_PROPOSED,
        FindingStatus.FIX_APPLIED,
        FindingStatus.VERIFICATION_PENDING,
        FindingStatus.VERIFIED_FIXED,
        FindingStatus.VERIFICATION_FAILED,
        FindingStatus.NOT_TESTED,
        FindingStatus.UNAVAILABLE,
    ]
    for s in states:
        assert isinstance(s.value, str)
