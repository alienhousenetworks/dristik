"""
WCAG 2.2 AA Accessibility & Usability Integration for CRO (Phase 6.7).

Bridges deep DOM accessibility auditing directly into conversion friction analysis.
Evaluates:
- WCAG 2.2 AA-oriented conversion checks (keyboard navigation, focus indicators, touch targets, contrast)
- Explicit disclosure of tests requiring manual assistive-technology review.

Notice: Automated accessibility screening is not proof of full WCAG 2.2 AA conformance.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.cro.accessibility.wcag_auditor import DeepWcagAuditor
from app.domain.models import PageEvidence, Finding
from app.domain.enums import Category, Severity, EvidenceClass


WCAG_MANUAL_REVIEW_TESTS: List[Dict[str, str]] = [
    {
        "test_name": "Screen Reader Flow & Pronunciation",
        "standard": "WCAG 2.2 Success Criterion 1.3.1 (Info and Relationships)",
        "why_manual": "Automated regexes cannot evaluate whether VoiceOver or NVDA reads complex interactive components in logical semantic order.",
    },
    {
        "test_name": "Keyboard Trap & Dynamic Focus Return",
        "standard": "WCAG 2.2 Success Criterion 2.1.2 (No Keyboard Trap)",
        "why_manual": "Testing that closing a modal or checkout drawer returns focus precisely to the triggering element requires live browser assistive-tech interaction.",
    },
    {
        "test_name": "Cognitive Clarity & Error Recovery",
        "standard": "WCAG 2.2 Success Criterion 3.3.4 (Error Prevention) & 3.3.8 (Accessible Authentication)",
        "why_manual": "Determining whether cognitive function tests (e.g., CAPTCHAs, memorization) prevent users with cognitive disabilities from completing transactions.",
    },
]

WCAG_DISCLAIMER = (
    "Automated accessibility screening was executed against crawled DOM elements. "
    "Automated tools detect approximately 30–40% of WCAG criteria. Full WCAG 2.2 AA "
    "conformance mandates manual review using assistive technology (NVDA, VoiceOver, keyboard-only traversal)."
)


class WcagCroConversionResult(BaseModel):
    accessibility_score: float = 85.0
    total_violations_found: int = 0
    contrast_issues_count: int = 0
    missing_labels_count: int = 0
    missing_alt_count: int = 0
    touch_target_violations_count: int = 0
    keyboard_outline_suppression_count: int = 0
    tests_requiring_manual_review: List[Dict[str, str]] = Field(default_factory=lambda: WCAG_MANUAL_REVIEW_TESTS)
    disclaimer: str = WCAG_DISCLAIMER
    wcag_findings: List[Finding] = Field(default_factory=list)


class WcagCroIntegrator:
    """Runs DeepWcagAuditor and synthesizes conversion-impacting accessibility findings."""

    @classmethod
    def evaluate(
        cls,
        pages: List[PageEvidence],
        raw_html_map: Optional[Dict[str, str]] = None,
    ) -> WcagCroConversionResult:
        # If pages don't have raw_html populated on page objects, populate from raw_html_map
        if raw_html_map:
            for p in pages:
                if not getattr(p, "raw_html", None) and p.url in raw_html_map:
                    p.raw_html = raw_html_map[p.url]

        wcag_summary, raw_findings = DeepWcagAuditor.audit_pages(pages)

        violations = wcag_summary.violations or []
        contrast_issues = sum(1 for v in violations if "1.4.3" in v.rule_id or "contrast" in v.description.lower())
        missing_lbl = sum(1 for v in violations if "label" in v.description.lower() or "1.3.1" in v.rule_id)
        missing_alt = sum(1 for v in violations if "1.1.1" in v.rule_id or "alt" in v.description.lower())
        touch_targets = sum(1 for v in violations if "2.5.8" in v.rule_id or "target size" in v.description.lower())
        focus_outline = sum(1 for v in violations if "2.4.7" in v.rule_id or "focus" in v.description.lower() or "outline" in v.description.lower())

        findings = []
        if focus_outline > 0:
            findings.append(Finding(
                finding_id="CRO-A11Y-001",
                title=f"Focus Indicator Suppression on Interactive Conversion Elements ({focus_outline} Count(s))",
                description="CSS suppresses focus outlines (e.g. `outline: none` without replacement), rendering keyboard-only navigation invisible.",
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                impact=3,
                effort=1,
                priority=1,
                recommendation="Provide a high-contrast focus indicator (e.g. `outline: 2px solid #2563eb; outline-offset: 2px`) on all `:focus-visible` interactive controls.",
                why_it_matters="Keyboard-only visitors cannot perceive which CTA or form field currently has focus, terminating their ability to convert.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="WCAG_2_2",
                epistemic_level="Deterministic DOM rule",
            ))

        if touch_targets > 0:
            findings.append(Finding(
                finding_id="CRO-A11Y-002",
                title=f"Sub-Optimal Touch Targets on Mobile Controls ({touch_targets} Instance(s))",
                description="Interactive buttons or links fail the WCAG 2.2 SC 2.5.8 minimum target size requirement of 24×24px (recommended 44×44px).",
                category=Category.UX_CONVERSION,
                severity=Severity.MEDIUM,
                impact=2,
                effort=1,
                priority=2,
                recommendation="Increase padding and tap bounds on all mobile conversion controls to at least 44×44px.",
                why_it_matters="Small touch targets cause tap inaccuracy, accidental navigations, and mobile checkout frustration.",
                evidence_class=EvidenceClass.OBSERVED,
                evidence_subtype="WCAG_2_2",
                epistemic_level="Deterministic DOM rule",
            ))

        return WcagCroConversionResult(
            accessibility_score=round(getattr(wcag_summary, "compliance_score", 85.0), 1),
            total_violations_found=getattr(wcag_summary, "violations_count", 0),
            contrast_issues_count=contrast_issues,
            missing_labels_count=missing_lbl,
            missing_alt_count=missing_alt,
            touch_target_violations_count=touch_targets,
            keyboard_outline_suppression_count=focus_outline,
            wcag_findings=findings,
        )


wcag_cro_integrator = WcagCroIntegrator()
