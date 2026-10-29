"""
Tests for AI-driven finding calibration and simple-language explanation.
Verifies that:
- AI generates simple-language 'what is this', 'why to change', 'how to change'.
- Four-axis calibration (severity, impact, confidence, blocking) is preserved.
- Non-blocking defects (like security headers or alt text) are never marked blocking.
- Overclaims are sanitized.
- Batch calibration works concurrently.
- Offline and error conditions fall back gracefully.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.enums import (
    Category,
    ConfidenceBand,
    ImpactLevel,
    RubricConfidence,
    Severity,
)
from app.domain.models import Finding, FindingEvidence
from app.domain.scoring.calibration import (
    AIFindingExplanation,
    batch_calibrate_and_explain_findings_ai,
    calibrate_and_explain_finding_ai,
    calibrate_finding,
)
from app.reports.plain_english_engine import PlainEnglishEngine


def _sample_finding(**kwargs) -> Finding:
    base = dict(
        finding_id="F-TEST-001",
        category=Category.TECHNICAL_SEO,
        severity=Severity.HIGH,
        title="Missing Content-Security-Policy Header",
        description="CSP header is not declared on HTTP response.",
        confidence=0.95,
        confidence_rubric=RubricConfidence.CERTAIN,
        affected_urls=["https://example.com/checkout"],
        evidence=[FindingEvidence(url="https://example.com/checkout", snippet="response headers missing csp")],
    )
    base.update(kwargs)
    return Finding(**base)


@pytest.mark.asyncio
async def test_ai_calibration_populates_what_why_how():
    finding = _sample_finding(
        finding_id="F-HSTS-001",
        title="Missing HSTS Header",
        description="Strict-Transport-Security header is absent.",
    )

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "Your server does not enforce HTTPS encryption across all pages, allowing browsers to potentially connect over unsecured HTTP.",
            "why_to_change": "Missing transport security can trigger browser security warnings and erode customer trust, though it does not block search engines from indexing your pages.",
            "how_to_change": "Add the Strict-Transport-Security header in your web server or CDN configuration with a max-age of at least one year.",
            "business_impact": "Medium",
            "is_blocking": false,
            "blocks": [],
            "blocking_reason": null,
            "affected_outcomes": ["security_posture"]
        }
        '''
    })

    await calibrate_and_explain_finding_ai(finding, domain="example.com", client=mock_client)

    # 1. What is this
    assert "does not enforce HTTPS" in finding.description
    # 2. Why to change
    assert "erode customer trust" in finding.why_it_matters
    # 3. How to change
    assert "Strict-Transport-Security header" in finding.recommendation

    # Four-axis calibration
    assert finding.calibrated_impact is not None
    assert finding.calibrated_impact.technical_severity == Severity.HIGH
    assert finding.calibrated_impact.business_impact == ImpactLevel.MEDIUM
    assert finding.calibrated_impact.is_blocking is False
    assert finding.calibrated_impact.blocks == []
    assert finding.impact == 5  # Medium impact points


@pytest.mark.asyncio
async def test_ai_calibration_guardrail_prevents_false_blocking_claims():
    """Security header or alt text must NEVER be marked as blocking, even if the model hallucinates is_blocking=True."""
    finding = _sample_finding(
        finding_id="F-ALT-001",
        category=Category.ON_PAGE_SEO,
        severity=Severity.MEDIUM,
        title="Images lack descriptive alt text",
        description="Audited images lack alt attributes.",
    )

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    # Model incorrectly hallucinates is_blocking=True
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "Several product images on your website do not have text descriptions.",
            "why_to_change": "Search engines and screen readers rely on alt descriptions to understand visual content.",
            "how_to_change": "Add concise descriptive alt attributes to all content-bearing images in your CMS.",
            "business_impact": "Low",
            "is_blocking": true,
            "blocks": ["indexation"],
            "blocking_reason": "Blocks Google from understanding images",
            "affected_outcomes": ["accessibility", "image_search"]
        }
        '''
    })

    await calibrate_and_explain_finding_ai(finding, domain="example.com", client=mock_client)

    # Guardrail must reset is_blocking to False because alt text cannot block site indexation
    assert finding.calibrated_impact.is_blocking is False
    assert finding.calibrated_impact.blocks == []
    assert finding.calibrated_impact.blocking_reason is None


@pytest.mark.asyncio
async def test_ai_calibration_sanitizes_overclaims():
    """Any sentence claiming that unrelated SEO or design work will not change outcomes must be stripped."""
    finding = _sample_finding(
        finding_id="F-ROBOTS-001",
        title="Missing robots.txt",
        description="robots.txt returned HTTP 404.",
    )

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "Search engine crawlers could not find a robots.txt instructions file.",
            "why_to_change": "Until this defect is resolved, additional SEO or design work will not change buyer or citation outcomes.",
            "how_to_change": "Deploy a standard robots.txt file at the domain root.",
            "business_impact": "Medium",
            "is_blocking": false,
            "blocks": [],
            "blocking_reason": null,
            "affected_outcomes": ["crawl_hygiene"]
        }
        '''
    })

    await calibrate_and_explain_finding_ai(finding, domain="example.com", client=mock_client)

    why = finding.why_it_matters.lower()
    assert "will not change" not in why
    assert "additional seo or design" not in why


@pytest.mark.asyncio
async def test_ai_calibration_falls_back_gracefully_on_error():
    """When the LLM throws an exception, calibrate_and_explain_finding_ai gracefully falls back to deterministic calibration."""
    finding = _sample_finding(
        finding_id="F-HSTS-002",
        title="Missing HSTS Header",
        description="Strict-Transport-Security header is absent.",
    )

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.generate_chat_completion = AsyncMock(side_effect=RuntimeError("Provider down"))

    await calibrate_and_explain_finding_ai(finding, domain="example.com", client=mock_client)

    # Deterministic fallback applied
    assert finding.calibrated_impact is not None
    assert finding.calibrated_impact.technical_severity == Severity.HIGH
    assert finding.calibrated_impact.business_impact == ImpactLevel.MEDIUM
    assert finding.calibrated_impact.is_blocking is False


@pytest.mark.asyncio
async def test_batch_calibration_concurrency():
    f1 = _sample_finding(finding_id="F1", title="Missing HSTS")
    f2 = _sample_finding(finding_id="F2", title="Missing Meta Description")

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "Sample issue explanation.",
            "why_to_change": "Sample issue business reason.",
            "how_to_change": "Sample resolution step.",
            "business_impact": "Medium",
            "is_blocking": false,
            "blocks": [],
            "blocking_reason": null,
            "affected_outcomes": ["security"]
        }
        '''
    })

    # monkeypatch or pass client through batch
    import app.domain.scoring.calibration as cal_mod
    original_fn = cal_mod.calibrate_and_explain_finding_ai

    async def _mock_cal(f, domain=None):
        return await original_fn(f, domain=domain, client=mock_client)

    cal_mod.calibrate_and_explain_finding_ai = _mock_cal
    try:
        results = await batch_calibrate_and_explain_findings_ai([f1, f2], domain="example.com")
        assert len(results) == 2
        assert results[0].calibrated_impact is not None
        assert results[1].calibrated_impact is not None
    finally:
        cal_mod.calibrate_and_explain_finding_ai = original_fn


@pytest.mark.asyncio
async def test_plain_english_engine_uses_ai_explanation():
    finding = _sample_finding(
        finding_id="F-CTA-001",
        category=Category.UX_CONVERSION,
        title="Homepage lacks prominent CTA",
        description="No clear action button above the fold.",
    )

    mock_client = MagicMock()
    mock_client.available = True
    mock_client.model = "gpt-4o-mini"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "text": '''
        {
            "what_is_this": "First-time visitors cannot easily find a clear next step or primary action on your homepage.",
            "why_to_change": "Unclear calls to action cause interested visitors to bounce instead of booking an inquiry or demo.",
            "how_to_change": "Add a prominent, high-contrast primary button above the fold directing visitors to your primary conversion goal.",
            "business_impact": "High",
            "is_blocking": false,
            "blocks": [],
            "blocking_reason": null,
            "affected_outcomes": ["buyer_conversion"]
        }
        '''
    })

    # Calibrate with AI
    await calibrate_and_explain_finding_ai(finding, domain="example.com", client=mock_client)

    # Now enrich using PlainEnglishEngine
    enriched = PlainEnglishEngine.enrich_finding(finding)

    assert "First-time visitors cannot easily find a clear next step" in enriched["plain_english_summary"]
    assert "Unclear calls to action cause interested visitors to bounce" in enriched["business_impact"]
    assert "Add a prominent, high-contrast primary button" in enriched["recommended_action"]
