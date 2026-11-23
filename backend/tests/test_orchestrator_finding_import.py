"""Stage-1 analyzer findings must construct the domain Finding model.

The deterministic analyzer emits metadata, schema, header, and redirect
findings. Those calls reference Finding directly. A missing import fails
the mission with NameError after the crawl has already finished.
"""
from app.domain.enums import Category, Severity
from app.domain.models import Finding
from app.orchestration import orchestrator as orchestrator_module


def test_orchestrator_binds_the_domain_finding_model():
    assert orchestrator_module.Finding is Finding


def test_stage1_extra_findings_match_the_domain_model():
    finding = Finding(
        finding_id="det_host_redirects_001",
        title="Host / Protocol Redirect Consolidation Defect",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        description="Host variants do not 301-consolidate.",
        recommendation="Enforce single-hop 301 redirects to the canonical HTTPS origin.",
        affected_urls=["https://perforacare.com"],
        confidence=0.9,
    )
    assert finding.category == Category.TECHNICAL_SEO
    assert finding.severity == Severity.HIGH
    assert finding.affected_urls == ["https://perforacare.com"]
