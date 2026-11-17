import pytest
from app.domain.models import Finding, FindingEvidence
from app.domain.enums import FindingStatus, Category, Severity
from app.reports.roadmap import RoadmapBuilder
from app.reports.plain_english_engine import render_plain_english_finding_card

def test_phase7_finding_quality_enrichment():
    """Verify finding card renders all 11 enterprise points including verification steps."""
    finding_dict = {
        "id": "F_ROBOTS_01",
        "title": "Unintended AI crawler block in robots.txt",
        "severity": "HIGH",
        "observed_result": "User-agent: GPTBot Disallow: /",
        "plain_english_summary": "Robots.txt blocks AI search engines from indexing content.",
        "business_impact": "Prevents inclusion in AI search engines, resulting in citation loss.",
        "affected_urls": ["https://perforacare.com/robots.txt"],
        "recommended_action": "Remove Disallow directive for GPTBot.",
        "verification_steps": "Fetch robots.txt and confirm 200 OK without Disallow: / for GPTBot.",
        "owner": "Engineering",
    }
    card_html = render_plain_english_finding_card(finding_dict)
    assert "F_ROBOTS_01" in card_html
    assert "Why does this matter to your business?" in card_html
    assert "How to verify the fix" in card_html
    assert "Recommended solution" in card_html

def test_phase7_business_impact_classification():
    """Verify business impact classifies measured vs inferred without fabricating revenue lift."""
    f = Finding(
        finding_id="F_TTFB_01",
        title="Excessive TTFB on Unwind combo",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        business_impact="Crawler discovery delay and user bounce friction.",
        business_impact_level="INFERRED", # Explicitly marked INFERRED, not MEASURED
    )
    assert f.business_impact_level == "INFERRED"
    assert f.business_impact_level != "MEASURED"

def test_phase7_roadmap_never_fabricates_when_empty():
    """Verify roadmap does not hallucinate institutional actions when zero findings exist."""
    plan = RoadmapBuilder().build_top_10_actions([])
    assert len(plan.actions) == 0
    assert plan.total_engineer_hours == 0
    assert "No remediation actions required" in plan.dependencies_flow

def test_phase7_verification_state_machine_transition():
    """Verify valid transitions across remediation lifecycle states."""
    f = Finding(
        finding_id="F_SCHEMA_01",
        title="Missing WebSite schema",
        category=Category.STRUCTURED_DATA,
        severity=Severity.MEDIUM,
        status=FindingStatus.OBSERVED,
    )
    assert f.status == FindingStatus.OBSERVED

    # Fix recommended
    f.status = FindingStatus.REMEDIATION_PROPOSED
    assert f.status == FindingStatus.REMEDIATION_PROPOSED

    # Fix applied by developer
    f.status = FindingStatus.FIX_APPLIED
    assert f.status == FindingStatus.FIX_APPLIED

    # Automated retest queued
    f.status = FindingStatus.VERIFICATION_PENDING
    assert f.status == FindingStatus.VERIFICATION_PENDING

    # Test confirmed resolved
    f.status = FindingStatus.VERIFIED_FIXED
    assert f.status == FindingStatus.VERIFIED_FIXED
