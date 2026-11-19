"""
Test Suite — Phase 9: Independent Verification Engine (10/10 Transformation)

Verifies all 5 sub-phases:
- 9.1: Verification Test Registry (All 13 condition categories)
- 9.2: Finding-Specific Acceptance Criteria (Machine-readable condition mapping)
- 9.3: Independent Retesting (Original vs new evidence comparison)
- 9.4: Cross-Discipline Regression Testing (Rendering, schema, layout, redirect loops, performance, links)
- 9.5: Verification State Machine (11 explicit states with strict evidence gating)
"""
import pytest
from datetime import datetime

from app.domain.models import Finding
from app.domain.enums import Category, Severity
from app.verification.models import (
    EvidenceComparisonRecord,
    MachineAcceptanceCriterion,
    RegressionCheckResult,
    TestCategory,
    VerificationRunReport,
    VerificationState,
)
from app.verification.test_registry import (
    VerificationTestRegistry,
    verification_test_registry,
)
from app.verification.acceptance_criteria import (
    AcceptanceCriteriaFactory,
    acceptance_criteria_factory,
)
from app.verification.retester import (
    IndependentRetester,
    independent_retester,
)
from app.verification.regression_engine import (
    CrossDisciplineRegressionEngine,
    cross_discipline_regression_engine,
)
from app.verification.state_machine import (
    VerificationStateMachine,
    verification_state_machine,
)
from app.verification.engine import (
    IndependentVerificationEngine,
    independent_verification_engine,
)


# ============================================================================
# Phase 9.1: Verification Test Registry (13 Categories)
# ============================================================================

def test_phase9_1_test_registry_all_13_categories():
    reg = verification_test_registry

    # 1. HTTP Condition
    r_http = reg.test_http_condition(status_code=200, expected_status=200, headers={"Content-Type": "text/html"})
    assert r_http.test_category == TestCategory.HTTP_CONDITION
    assert r_http.passed is True

    # 2. HTML Condition
    r_html = reg.test_html_condition("<!DOCTYPE html><html><head><meta charset='utf-8'></head><body><h1>Hi</h1></body></html>")
    assert r_html.test_category == TestCategory.HTML_CONDITION
    assert r_html.passed is True

    # 3. DOM Condition
    r_dom = reg.test_dom_condition("<html><body><button class='cta-btn'>Start Trial</button></body></html>", target_selector=".cta-btn", expected_text="Start Trial")
    assert r_dom.test_category == TestCategory.DOM_CONDITION
    assert r_dom.passed is True

    # 4. Metadata
    r_meta = reg.test_metadata("<html><head><title>Enterprise SEO Platform</title><meta name='description' content='Full platform capabilities description for enterprise digital teams.'></head></html>")
    assert r_meta.test_category == TestCategory.METADATA
    assert r_meta.passed is True

    # 5. Schema
    r_schema = reg.test_schema('<html><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "Dristik"}</script></html>', required_type="Organization")
    assert r_schema.test_category == TestCategory.SCHEMA
    assert r_schema.passed is True

    # 6. Internal Links
    r_links = reg.test_internal_links("<html><body><a href='/pricing'>Pricing</a></body></html>", target_link="/pricing", target_resolves_200=True)
    assert r_links.test_category == TestCategory.INTERNAL_LINKS
    assert r_links.passed is True

    # 7. Accessibility
    r_a11y = reg.test_accessibility("<html><body><img src='logo.png' alt='Company Logo'></body></html>")
    assert r_a11y.test_category == TestCategory.ACCESSIBILITY
    assert r_a11y.passed is True

    # 8. Performance
    r_perf = reg.test_performance(ttfb_ms=190.0, max_ttfb_ms=300.0)
    assert r_perf.test_category == TestCategory.PERFORMANCE
    assert r_perf.passed is True

    # 9. Visual Layout
    r_layout = reg.test_visual_layout("<html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'></head></html>")
    assert r_layout.test_category == TestCategory.VISUAL_LAYOUT
    assert r_layout.passed is True

    # 10. Form Behaviour
    r_form = reg.test_form_behaviour("<html><body><form><input id='email' aria-label='Email' type='text'></form></body></html>")
    assert r_form.test_category == TestCategory.FORM_BEHAVIOUR
    assert r_form.passed is True

    # 11. AI Answer Outcome
    r_ai = reg.test_ai_answer_outcome(
        "<html><body><h1>What is Dristik?</h1><p>Dristik is an enterprise AI search and discovery intelligence platform engineered to measure and remediate digital brand visibility across modern LLMs and search engines.</p></body></html>",
        target_question="What is Dristik platform?",
    )
    assert r_ai.test_category == TestCategory.AI_ANSWER_OUTCOME
    assert r_ai.passed is True

    # 12. Search Performance (Robots.txt)
    r_search = reg.test_search_performance("User-agent: GPTBot\nAllow: /\nUser-agent: *\nDisallow: /admin", bot_name="GPTBot")
    assert r_search.test_category == TestCategory.SEARCH_PERFORMANCE
    assert r_search.passed is True

    # 13. Analytics Events
    r_analytics = reg.test_analytics_events("<html><head><script src='https://www.googletagmanager.com/gtm.js?id=GTM-123'></script></head></html>")
    assert r_analytics.test_category == TestCategory.ANALYTICS_EVENTS
    assert r_analytics.passed is True


# ============================================================================
# Phase 9.2: Finding-Specific Acceptance Criteria
# ============================================================================

def test_phase9_2_machine_readable_acceptance_criteria_mapping():
    factory = acceptance_criteria_factory

    # 1. Missing title
    f_title = Finding(finding_id="F_TITLE_01", title="Missing or Empty Title Tag", category=Category.ON_PAGE_SEO, severity=Severity.HIGH)
    c_title = factory.create_criterion_for_finding(f_title)
    assert c_title.test_category == TestCategory.METADATA
    assert c_title.min_value == 10.0
    assert c_title.max_value == 70.0

    # 2. Missing Alt Text
    f_alt = Finding(finding_id="F_ALT_01", title="Missing Image Alt Text", category=Category.ON_PAGE_SEO, severity=Severity.MEDIUM)
    c_alt = factory.create_criterion_for_finding(f_alt)
    assert c_alt.test_category == TestCategory.ACCESSIBILITY
    assert c_alt.target_attribute == "alt"

    # 3. Invalid Schema
    f_schema = Finding(finding_id="F_SCHEMA_01", title="Invalid FAQPage Schema Structure", category=Category.SCHEMA, severity=Severity.HIGH)
    c_schema = factory.create_criterion_for_finding(f_schema)
    assert c_schema.test_category == TestCategory.SCHEMA
    assert c_schema.expected_value_pattern == "FAQPage"

    # 4. Broken Internal Link
    f_link = Finding(finding_id="F_LINK_01", title="Broken Internal Link Returning 404", category=Category.TECHNICAL_SEO, severity=Severity.HIGH)
    c_link = factory.create_criterion_for_finding(f_link)
    assert c_link.test_category == TestCategory.INTERNAL_LINKS

    # 5. CTA Failure
    f_cta = Finding(finding_id="F_CTA_01", title="Hero CTA Button Destination Failure", category=Category.UX_CONVERSION, severity=Severity.HIGH)
    c_cta = factory.create_criterion_for_finding(f_cta)
    assert c_cta.test_category == TestCategory.DOM_CONDITION

    # 6. Missing Form Label
    f_form = Finding(finding_id="F_FORM_01", title="Missing Accessible Form Input Label", category=Category.UX_CONVERSION, severity=Severity.MEDIUM)
    c_form = factory.create_criterion_for_finding(f_form)
    assert c_form.test_category == TestCategory.FORM_BEHAVIOUR

    # 7. Missing Answer
    f_aeo = Finding(finding_id="F_AEO_01", title="Missing Answer to Pricing Commercial Query", category=Category.AI_SEARCH, severity=Severity.HIGH)
    c_aeo = factory.create_criterion_for_finding(f_aeo)
    assert c_aeo.test_category == TestCategory.AI_ANSWER_OUTCOME

    # 8. Robots AI Crawler Block
    f_robots = Finding(finding_id="F_ROBOTS_01", title="Robots.txt Disallow Directive for AI Crawlers", category=Category.GEO, severity=Severity.CRITICAL)
    c_robots = factory.create_criterion_for_finding(f_robots)
    assert c_robots.test_category == TestCategory.SEARCH_PERFORMANCE


# ============================================================================
# Phase 9.3: Independent Retesting & Evidence Comparison
# ============================================================================

def test_phase9_3_independent_retesting_evidence_comparison():
    retester = independent_retester
    f = Finding(finding_id="F_TITLE_01", title="Missing Title Tag", category=Category.ON_PAGE_SEO, severity=Severity.HIGH)
    baseline_ev = {"html": "<html><head></head><body>No title</body></html>", "defect_severity_score": 10}

    # Case 1: Post-deploy HTML has valid title -> Retest PASS
    post_deploy_pass = {"html": "<html><head><title>Dristik - Enterprise AI Search Intelligence</title></head><body>Fixed</body></html>"}
    res_pass: EvidenceComparisonRecord = retester.retest_finding(f, baseline_ev, post_deploy_pass)
    assert res_pass.verification_passed is True
    assert res_pass.current_finding_state == VerificationState.VERIFIED_FIXED
    assert "passed=True" in res_pass.details

    # Case 2: Post-deploy HTML has short/empty title -> Retest FAIL
    post_deploy_fail = {"html": "<html><head><title>Hi</title></head><body>Too short</body></html>", "defect_severity_score": 10}
    res_fail = retester.retest_finding(f, baseline_ev, post_deploy_fail)
    assert res_fail.verification_passed is False
    assert res_fail.current_finding_state == VerificationState.FAILED

    # Case 3: Partial fix (defect severity reduced from 10 to 5)
    post_deploy_partial = {"html": "<html><head><title>Hi</title></head><body>Better</body></html>", "defect_severity_score": 5}
    res_partial = retester.retest_finding(f, baseline_ev, post_deploy_partial)
    assert res_partial.verification_passed is False
    assert res_partial.partially_fixed is True
    assert res_partial.current_finding_state == VerificationState.PARTIALLY_FIXED


# ============================================================================
# Phase 9.4: Cross-Discipline Regression Testing
# ============================================================================

def test_phase9_4_cross_discipline_regressions():
    reg = cross_discipline_regression_engine
    base_ev = {"ttfb_ms": 150.0}

    # 1. Clean post-deploy evidence -> No regression
    clean_ev = {"html": "<html><head><title>Title</title></head><body><p>Clean</p></body></html>", "ttfb_ms": 160.0}
    r_clean = reg.check_regressions(base_ev, clean_ev)
    assert r_clean.has_regression is False

    # 2. Template rendering regression (unbalanced HTML)
    broken_html = "<html><head><title>Title</title></head><body><div><div><div><p>Unclosed blocks" + ("<div>" * 20) + "</body></html>"
    r_render = reg.check_regressions(base_ev, {"html": broken_html, "ttfb_ms": 160.0})
    assert r_render.has_regression is True
    assert r_render.regression_type == "METADATA_RENDER"

    # 3. Schema regression (invalid JSON-LD)
    broken_schema = "<html><head><script type='application/ld+json'>{bad json here}</script></head></html>"
    r_schema = reg.check_regressions(base_ev, {"html": broken_schema, "ttfb_ms": 160.0})
    assert r_schema.has_regression is True
    assert r_schema.regression_type == "SCHEMA_SYNTAX"

    # 4. Redirect loop regression
    r_loop = reg.check_regressions(base_ev, {"html": "<html></html>", "redirect_chain": ["/a", "/b", "/a"]})
    assert r_loop.has_regression is True
    assert r_loop.regression_type == "REDIRECT_LOOP"

    # 5. Performance spike regression (TTFB spiked from 150ms to 650ms)
    r_perf = reg.check_regressions(base_ev, {"html": "<html></html>", "ttfb_ms": 650.0})
    assert r_perf.has_regression is True
    assert r_perf.regression_type == "PERFORMANCE_SPIKE"

    # 6. Navigation broken link regression
    r_nav = reg.check_regressions(base_ev, {"html": "<html></html>", "broken_internal_links": ["/broken-page-404"]})
    assert r_nav.has_regression is True
    assert r_nav.regression_type == "BROKEN_LINKS"


# ============================================================================
# Phase 9.5: Verification State Machine (11 States)
# ============================================================================

def test_phase9_5_verification_state_machine_11_states():
    sm = verification_state_machine

    # 1. State machine progression
    sm.validate_transition(VerificationState.OPEN, VerificationState.IN_PROGRESS)
    sm.validate_transition(VerificationState.IN_PROGRESS, VerificationState.PATCH_READY)
    sm.validate_transition(VerificationState.PATCH_READY, VerificationState.APPROVED)
    sm.validate_transition(VerificationState.APPROVED, VerificationState.DEPLOYED)
    sm.validate_transition(VerificationState.DEPLOYED, VerificationState.VERIFICATION_PENDING)

    # 2. Rejection of illegal state jump (e.g. OPEN directly to VERIFIED_FIXED)
    with pytest.raises(ValueError):
        sm.validate_transition(VerificationState.OPEN, VerificationState.VERIFIED_FIXED)

    # 3. Gating on VERIFIED_FIXED: cannot close without passed evidence comparison
    fail_ev = EvidenceComparisonRecord(
        finding_id="F_01",
        original_finding_summary="Defect",
        current_finding_state=VerificationState.FAILED,
        verification_passed=False,
    )
    with pytest.raises(ValueError):
        sm.validate_transition(VerificationState.VERIFICATION_PENDING, VerificationState.VERIFIED_FIXED, evidence_comparison=fail_ev)

    # 4. Gating on VERIFIED_FIXED: cannot close if regression is detected
    pass_ev = EvidenceComparisonRecord(
        finding_id="F_01",
        original_finding_summary="Defect",
        current_finding_state=VerificationState.VERIFIED_FIXED,
        verification_passed=True,
    )
    reg_detected = RegressionCheckResult(has_regression=True, details="Mobile overflow")
    with pytest.raises(ValueError):
        sm.validate_transition(VerificationState.VERIFICATION_PENDING, VerificationState.VERIFIED_FIXED, evidence_comparison=pass_ev, regression_result=reg_detected)

    # 5. Clean pass allows transition to VERIFIED_FIXED
    clean_reg = RegressionCheckResult(has_regression=False)
    sm.validate_transition(VerificationState.VERIFICATION_PENDING, VerificationState.VERIFIED_FIXED, evidence_comparison=pass_ev, regression_result=clean_reg)

    # 6. Accepted Risk transition
    sm.validate_transition(VerificationState.OPEN, VerificationState.ACCEPTED_RISK)


# ============================================================================
# Phase 9 Master Independent Verification E2E
# ============================================================================

def test_phase9_master_independent_verification_e2e():
    engine = independent_verification_engine
    f = Finding(
        finding_id="F_SCHEMA_E2E",
        title="Missing Organization Schema Markup",
        category=Category.SCHEMA,
        severity=Severity.HIGH,
    )

    baseline_ev = {
        "html": "<html><head><title>My Company</title></head><body>No schema here</body></html>",
        "ttfb_ms": 170.0,
    }

    # Case 1: Post-deployment crawl resolves schema cleanly with zero regressions
    post_deploy_clean = {
        "html": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>My Company</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "My Company",
                "url": "https://mycompany.com"
            }
            </script>
        </head>
        <body>Clean content</body>
        </html>
        """,
        "ttfb_ms": 175.0,
    }

    report_pass: VerificationRunReport = engine.execute_independent_verification(
        finding=f,
        baseline_evidence=baseline_ev,
        post_deploy_evidence=post_deploy_clean,
    )

    assert report_pass.retest_passed is True
    assert report_pass.regression_detected is False
    assert report_pass.final_state == VerificationState.VERIFIED_FIXED
    assert report_pass.is_10_of_10_compliant is True

    # Case 2: Post-deployment crawl introduced invalid JSON schema regression
    post_deploy_broken = {
        "html": "<html><head><script type='application/ld+json'>{bad_json: 123}</script></head></html>",
        "ttfb_ms": 180.0,
    }

    report_broken: VerificationRunReport = engine.execute_independent_verification(
        finding=f,
        baseline_evidence=baseline_ev,
        post_deploy_evidence=post_deploy_broken,
    )

    assert report_broken.regression_detected is True
    assert report_broken.final_state in [VerificationState.FAILED, VerificationState.REOPENED]
