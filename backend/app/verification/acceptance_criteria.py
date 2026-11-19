"""
Finding-Specific Acceptance Criteria Factory — Phase 9.2 (10/10 Transformation)

Maps any audit finding to an explicit, machine-readable acceptance condition:
- Missing title -> Meaningful title exists (10 <= length <= 70)
- Missing alt text -> Contextual alt attribute exists on images
- Invalid schema -> Required syntax and applicable properties validate
- Broken internal link -> Target resolves successfully (200 OK)
- CTA failure -> Intended destination works with non-empty URL
- Missing form label -> Accessible label is present on input
- Missing answer -> Required factual answer exists and is supported
- Robots block -> Unintended crawler block directive removed
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.verification.models import (
    MachineAcceptanceCriterion,
    TestCategory,
)

logger = logging.getLogger("dristik.verification.criteria")


class AcceptanceCriteriaFactory:
    """
    Synthesizes machine-readable acceptance contracts for findings.
    """

    @classmethod
    def create_criterion_for_finding(cls, finding: Any) -> MachineAcceptanceCriterion:
        f_id = getattr(finding, "finding_id", None) or getattr(finding, "id", "F_DEFAULT")
        title = (getattr(finding, "title", None) or "").lower()
        desc = (getattr(finding, "description", None) or "").lower()
        cat = str(getattr(finding, "category", "")).upper()

        crit_id = f"CRIT_{f_id}"

        # 1. Missing Title
        if "title" in title and ("missing" in title or "empty" in title or "length" in title or "short" in title):
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.METADATA,
                condition_name="Title Tag Quality Criterion",
                expected_condition_text="Meaningful title exists (10 <= length <= 70 characters).",
                target_selector="title",
                min_value=10.0,
                max_value=70.0,
            )

        # 2. Missing Alt Text
        if "alt" in title or "alt text" in desc:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.ACCESSIBILITY,
                condition_name="Image Alt Text Criterion",
                expected_condition_text="All content images possess descriptive contextual alt text.",
                target_selector="img",
                target_attribute="alt",
            )

        # 3. Invalid Schema
        if "schema" in title or "structured data" in title or "json-ld" in desc:
            req_type = "Organization"
            if "faq" in title or "faq" in desc:
                req_type = "FAQPage"
            elif "product" in title or "product" in desc:
                req_type = "Product"

            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.SCHEMA,
                condition_name="Schema Validation Criterion",
                expected_condition_text=f"Valid JSON-LD schema with @type='{req_type}' and required properties.",
                expected_value_pattern=req_type,
            )

        # 4. Broken Internal Link
        if "broken link" in title or "404" in title or "internal link" in title:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.INTERNAL_LINKS,
                condition_name="Internal Link Resolution Criterion",
                expected_condition_text="Target internal URL resolves with HTTP 200 without redirect loops.",
            )

        # 5. CTA Failure
        if "cta" in title or "call to action" in title or "button" in desc:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.DOM_CONDITION,
                condition_name="Primary CTA Functionality Criterion",
                expected_condition_text="Intended destination works; CTA element exists with non-empty href.",
                target_selector="button, a.cta, a.btn",
            )

        # 6. Missing Form Label
        if "form" in title or "label" in title or "input" in desc:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.FORM_BEHAVIOUR,
                condition_name="Form Input Label Accessibility Criterion",
                expected_condition_text="Every visible form input has an accessible <label> or aria-label.",
                target_selector="input",
            )

        # 7. Missing Answer / AEO
        if "answer" in title or "unanswered" in title or "aeo" in cat.lower() or "faq" in title:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.AI_ANSWER_OUTCOME,
                condition_name="AI Answer Coverage Criterion",
                expected_condition_text="Required factual answer exists in a 20-40 word self-contained passage.",
            )

        # 8. Robots AI Crawler Block
        if "robots" in title or "crawler block" in title or "gptbot" in title:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.SEARCH_PERFORMANCE,
                condition_name="Robots.txt AI Bot Allowance Criterion",
                expected_condition_text="Robots.txt allows AI search engine user-agents to crawl / without disallow directives.",
            )

        # 9. Performance / TTFB
        if "ttfb" in title or "latency" in title or "performance" in title:
            return MachineAcceptanceCriterion(
                criterion_id=crit_id,
                finding_id=f_id,
                test_category=TestCategory.PERFORMANCE,
                condition_name="TTFB Performance Criterion",
                expected_condition_text="Observed TTFB is under 300ms threshold under comparable network conditions.",
                max_value=300.0,
            )

        # Default Fallback: DOM condition
        return MachineAcceptanceCriterion(
            criterion_id=crit_id,
            finding_id=f_id,
            test_category=TestCategory.DOM_CONDITION,
            condition_name="Defect Elimination Criterion",
            expected_condition_text=f"Defect condition '{title}' is no longer observed.",
        )


acceptance_criteria_factory = AcceptanceCriteriaFactory()
