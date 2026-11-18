import pytest
from typing import List
from app.domain.models import (
    ExecutiveReport,
    Finding,
    Category,
    Severity,
    OverallScoreResult,
    CategoryScore,
    PageReport,
    CroAuditReport,
    CtaAnalysisRollup,
    CtaAuditItem,
    SocialProofAuditRollup,
    PricingPsychologyRollup,
    ValuePropClarityAudit,
    FormAuditReport,
    FormAuditItem,
)
from app.reports.adaptive_audit_book import (
    _build_ch_cro_cta,
    _build_ch_cro_trust,
    _build_ch_cro_forms,
    _build_ch_cro_value_prop,
    _build_ch_conversion,
    build_adaptive_publication_document,
)
from app.cro.engine import build_from_executive_report
from app.cro.reporting import render_cro_audit_book


def _create_mock_cro_report() -> ExecutiveReport:
    """Creates a mock executive report with rich hierarchical CRO crawl data."""
    cta_items = [
        CtaAuditItem(
            page_url="https://example.com/",
            cta_text="Claim Your Free Assessment",
            element_type="button",
            target_url="https://example.com/start",
            intent_category="HIGH_INTENT",
            placement_zone="HERO",
            suggested_rewrite="Claim Free Assessment Today",
        ),
        CtaAuditItem(
            page_url="https://example.com/pricing",
            cta_text="Learn More",
            element_type="a",
            target_url="https://example.com/details",
            intent_category="EXPLORATORY",
            placement_zone="BODY",
        ),
    ]

    form_items = [
        FormAuditItem(
            page_url="https://example.com/contact",
            form_action="/api/submit",
            input_count=4,
            missing_labels_count=0,
            submit_button_text="Send Inquiry",
        ),
        FormAuditItem(
            page_url="https://example.com/demo",
            form_action="/api/demo",
            input_count=6,
            missing_labels_count=1,
            submit_button_text="Book Demo",
        ),
    ]

    cro_audit = CroAuditReport(
        overall_cro_score=82.0,
        cro_grade="B",
        cta_analysis=CtaAnalysisRollup(
            total_ctas_detected=2,
            high_intent_count=1,
            exploratory_count=1,
            has_hero_cta=True,
            hero_cta_text="Claim Your Free Assessment",
            ctas=cta_items,
            action_clarity_score=85.0,
        ),
        social_proof=SocialProofAuditRollup(
            total_testimonials=14,
            client_logos_detected=6,
            quantified_proof_claims=["Over 50,000 businesses supported", "99.4% uptime SLA"],
            trust_badges_detected=["SOC2 Type II Certified", "ISO 27001"],
            has_privacy_policy=True,
            has_terms_of_service=True,
            trust_authority_score=88.0,
        ),
        pricing_psychology=PricingPsychologyRollup(
            pricing_page_detected=True,
            pricing_url="https://example.com/pricing",
            has_money_back_guarantee=True,
            guarantee_signals=["30-Day Money Back Guarantee", "No questions asked refund"],
            commercial_transparency_score=90.0,
        ),
        value_prop=ValuePropClarityAudit(
            hero_headline="Enterprise Data Visibility for Modern Teams",
            headline_word_count=7,
            customer_centricity_ratio=0.75,
            has_adjacent_cta=True,
            clarity_grade="A",
            observations=["Headline concisely identifies target audience and core value."],
        ),
        form_friction=FormAuditReport(
            total_forms_detected=2,
            forms=form_items,
            forms_with_missing_labels=1,
            cro_friction_grade="B",
            friction_score=22.0,
        ),
    )

    page_reports = [
        PageReport(
            url="https://example.com/",
            status_code=200,
            title="Home | Example Enterprise Suite",
            h1_tags=["Enterprise Data Visibility for Modern Teams"],
            is_homepage=True,
            word_count=650,
        ),
        PageReport(
            url="https://example.com/pricing",
            status_code=200,
            title="Pricing Plans | Example",
            h1_tags=["Transparent Enterprise Pricing"],
            is_homepage=False,
            word_count=420,
        ),
    ]

    findings = [
        Finding(
            finding_id="FIND-CTA-001",
            category=Category.UX_CONVERSION,
            title="Generic secondary CTA microcopy on pricing page",
            description="The pricing page uses passive 'Learn More' buttons rather than active value triggers.",
            severity=Severity.MEDIUM,
            impact=6,
            recommendation="Replace 'Learn More' with 'View Tier Details' or 'Compare Features'.",
        ),
        Finding(
            finding_id="FIND-FORM-001",
            category=Category.UX_CONVERSION,
            title="Demo form contains missing input labels",
            description="One input in the demo form lacks an explicit accessible label attribute.",
            severity=Severity.HIGH,
            impact=8,
            recommendation="Add explicit <label for='...'> tags for every input element.",
        ),
        Finding(
            finding_id="FIND-TRUST-001",
            category=Category.UX_CONVERSION,
            title="Security badges missing in close proximity to final checkout action",
            description="SOC2 badges are rendered in the footer but not adjacent to the primary conversion button.",
            severity=Severity.LOW,
            impact=3,
            recommendation="Place trust badges within 50px of the primary conversion button.",
        ),
    ]

    scores = OverallScoreResult(
        overall_score=82.0,
        grade="B",
        health_label="Good",
        website_geo_readiness_score=75.0,
        observed_ai_visibility_score=60.0,
        aeo_readiness_score=70.0,
        category_scores={
            "UX_CONVERSION": CategoryScore(
                category=Category.UX_CONVERSION,
                score=82.0,
                grade="B",
                health_label="Good",
            )
        },
    )

    return ExecutiveReport(
        org_id="test_org",
        report_id="RUN_CRO_TEST01",
        analysis_id="RUN_CRO_TEST01",
        audit_id="RUN_CRO_TEST01",
        domain="example.com",
        website_url="https://example.com",
        company_name="Example Corp",
        generated_at="2026-10-15T12:00:00Z",
        scores=scores,
        story_summary="CRO audit mock report.",
        primary_strategic_opportunity="Optimize conversion triggers.",
        consultant_advice_what_to_ignore="Ignore minor low-impact keywords.",
        page_reports=page_reports,
        cro_audit=cro_audit,
        findings=findings,
    )


def test_cro_audit_report_bridge_properties():
    """Verify CroAuditReport property bridge accurately surfaces hierarchical data."""
    report = _create_mock_cro_report()
    cro = report.cro_audit
    assert cro is not None

    # Primary CTA & CTA inventory
    assert cro.primary_cta_text == "Claim Your Free Assessment"
    assert len(cro.ctas) == 2
    assert len(cro.cta_inventory) == 2
    assert cro.ctas[0].text == "Claim Your Free Assessment"
    assert cro.ctas[0].location == "HERO"
    assert "High Intent" in cro.ctas[0].role

    # Trust signals
    signals = cro.trust_signals
    assert len(signals) >= 4
    signal_names = [s["name"] for s in signals]
    assert "Trust Badge / Certification" in signal_names
    assert "Quantified Proof Claim" in signal_names
    assert "Customer Testimonials" in signal_names
    assert "Guarantee / Risk Reversal" in signal_names

    # Form audit bridge
    assert cro.form_audit is not None
    assert len(cro.form_audit.forms) == 2
    form0 = cro.form_audit.forms[0]
    assert form0.field_count == 4
    assert form0.cta_text == "Send Inquiry"
    assert form0.has_labels is True


def test_cta_chapter_rendering():
    """Verify CTA chapter renders real crawl data instead of 'NOT MEASURED'."""
    report = _create_mock_cro_report()
    html = _build_ch_cro_cta(report, {})

    # Must display the real hero CTA
    assert "Claim Your Free Assessment" in html
    assert 'NOT MEASURED' not in html
    # Must display observed CTA inventory
    assert "No individual CTA inventory records were captured" not in html
    assert "Claim Free Assessment Today" in html
    # Must only display CTA findings
    assert "FIND-CTA-001" in html
    assert "FIND-FORM-001" not in html


def test_trust_chapter_rendering():
    """Verify Trust chapter renders trust badges and guarantee signals."""
    report = _create_mock_cro_report()
    html = _build_ch_cro_trust(report, {})

    assert "SOC2 Type II Certified" in html
    assert "30-Day Money Back Guarantee" in html
    assert "No verified trust-signal inventory records were captured" not in html
    # Must only display Trust findings
    assert "FIND-TRUST-001" in html
    assert "FIND-FORM-001" not in html


def test_forms_chapter_rendering():
    """Verify Form chapter renders forms from cro_audit.form_friction."""
    report = _create_mock_cro_report()
    html = _build_ch_cro_forms(report, {})

    assert "No interactive form audit records were captured" not in html
    assert "5.0 Avg" in html  # (4 + 6) / 2 = 5.0
    assert "2 Form(s)" in html
    assert "Send Inquiry" in html
    # Must only display Form findings
    assert "FIND-FORM-001" in html
    assert "FIND-CTA-001" not in html


def test_value_prop_and_conversion_master_chapters():
    """Verify Value Prop chapter and Master Book Chapter 10 render real data."""
    report = _create_mock_cro_report()

    # Value Prop
    vp_html = _build_ch_cro_value_prop(report, {})
    assert "Grade A" in vp_html
    assert "Enterprise Data Visibility for Modern Teams" in vp_html

    # Master Book Chapter 10
    ch10_html = _build_ch_conversion(report, {})
    assert 'Primary CTA detected: "Claim Your Free Assessment"' in ch10_html
    assert "Enterprise Data Visibility for Modern Teams" in ch10_html


def test_engine_reconciles_page_reports_and_findings():
    """Verify build_from_executive_report falls back to page_reports and reconciles findings."""
    report = _create_mock_cro_report()
    # Explicitly ensure crawl_manifest is None to test fallback
    report.crawl_manifest = None

    intel = build_from_executive_report(report)
    assert intel.sample_size == 2
    assert len(intel.findings) >= 3

    finding_summaries = [f.finding for f in intel.findings]
    assert any("Generic secondary CTA" in s for s in finding_summaries)
    assert any("Demo form contains missing" in s for s in finding_summaries)
    assert any("Security badges missing" in s for s in finding_summaries)


def test_standalone_cro_audit_book_publication():
    """Verify render_cro_audit_book returns a complete publication-grade HTML document."""
    report = _create_mock_cro_report()
    html = render_cro_audit_book(report)

    assert "<!DOCTYPE html>" in html
    assert "Conversion Experience &amp; CRO Audit" in html or "Conversion Experience & CRO Audit" in html
    assert "Call-to-Action (CTA) Hierarchy &amp; Friction Audit" in html or "Call-to-Action (CTA) Hierarchy & Friction Audit" in html
    assert "Claim Your Free Assessment" in html
    assert "SOC2 Type II Certified" in html
