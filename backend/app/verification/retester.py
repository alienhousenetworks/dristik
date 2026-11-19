"""
Independent Retesting Engine — Phase 9.3 (10/10 Transformation)

Executes objective, reproducible retests comparing original baseline evidence
against post-deployment crawl captures under equivalent test conditions:
- Original evidence
- New evidence
- Original finding
- Current finding state
- Test environment
- Timestamp
- Verification result
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.verification.acceptance_criteria import (
    AcceptanceCriteriaFactory,
    acceptance_criteria_factory,
)
from app.verification.models import (
    EvidenceComparisonRecord,
    MachineAcceptanceCriterion,
    TestCategory,
    TestExecutionResult,
    VerificationState,
)
from app.verification.test_registry import (
    VerificationTestRegistry,
    verification_test_registry,
)

logger = logging.getLogger("dristik.verification.retester")


class IndependentRetester:
    """
    Evaluates post-deployment evidence against baseline evidence independently.
    """

    def __init__(self, registry: Optional[VerificationTestRegistry] = None):
        self.registry = registry or verification_test_registry

    def evaluate_criterion(
        self,
        criterion: MachineAcceptanceCriterion,
        post_deploy_data: Dict[str, Any],
    ) -> TestExecutionResult:
        cat = criterion.test_category
        html = post_deploy_data.get("html", "")
        status_code = post_deploy_data.get("status_code", 200)
        headers = post_deploy_data.get("headers", {})
        ttfb = post_deploy_data.get("ttfb_ms", 180.0)
        robots_txt = post_deploy_data.get("robots_txt", "")

        if cat == TestCategory.METADATA:
            min_l = int(criterion.min_value or 10)
            max_l = int(criterion.max_value or 70)
            req_meta = "meta" in criterion.condition_name.lower() or "description" in criterion.condition_name.lower()
            return self.registry.test_metadata(html, min_title_len=min_l, max_title_len=max_l, require_meta_desc=req_meta)

        elif cat == TestCategory.ACCESSIBILITY:
            return self.registry.test_accessibility(html)

        elif cat == TestCategory.SCHEMA:
            req_type = criterion.expected_value_pattern or "Organization"
            return self.registry.test_schema(html, required_type=req_type)

        elif cat == TestCategory.INTERNAL_LINKS:
            target_link = post_deploy_data.get("target_link", "/")
            target_resolves = post_deploy_data.get("target_resolves_200", True)
            return self.registry.test_internal_links(html, target_link, target_resolves_200=target_resolves)

        elif cat == TestCategory.DOM_CONDITION:
            sel = criterion.target_selector or "button"
            return self.registry.test_dom_condition(html, target_selector=sel, should_exist=True)

        elif cat == TestCategory.FORM_BEHAVIOUR:
            return self.registry.test_form_behaviour(html)

        elif cat == TestCategory.AI_ANSWER_OUTCOME:
            question = post_deploy_data.get("question", "What is the product?")
            return self.registry.test_ai_answer_outcome(html, target_question=question)

        elif cat == TestCategory.SEARCH_PERFORMANCE:
            return self.registry.test_search_performance(robots_txt, bot_name="GPTBot")

        elif cat == TestCategory.PERFORMANCE:
            max_t = criterion.max_value or 300.0
            return self.registry.test_performance(ttfb, max_ttfb_ms=max_t)

        elif cat == TestCategory.HTTP_CONDITION:
            exp_status = int(criterion.min_value or 200)
            return self.registry.test_http_condition(status_code=status_code, expected_status=exp_status, headers=headers)

        elif cat == TestCategory.VISUAL_LAYOUT:
            return self.registry.test_visual_layout(html)

        elif cat == TestCategory.ANALYTICS_EVENTS:
            return self.registry.test_analytics_events(html)

        # Default fallback
        return self.registry.test_html_condition(html)

    def retest_finding(
        self,
        finding: Any,
        original_evidence: Dict[str, Any],
        new_evidence: Dict[str, Any],
        test_environment: str = "PRODUCTION",
        custom_criterion: Optional[MachineAcceptanceCriterion] = None,
    ) -> EvidenceComparisonRecord:
        f_id = getattr(finding, "finding_id", None) or getattr(finding, "id", "F_DEFAULT")
        summary = getattr(finding, "title", "Audit Finding")

        criterion = custom_criterion or acceptance_criteria_factory.create_criterion_for_finding(finding)
        test_res = self.evaluate_criterion(criterion, new_evidence)

        # Determine verification result
        verification_passed = test_res.passed
        partially_fixed = False

        if not verification_passed:
            # Check if partially fixed (e.g. improved but not fully matching criterion)
            orig_val = original_evidence.get("defect_severity_score", 10)
            new_val = new_evidence.get("defect_severity_score", 5)
            if new_val < orig_val:
                partially_fixed = True

        state = (
            VerificationState.VERIFIED_FIXED if verification_passed
            else (VerificationState.PARTIALLY_FIXED if partially_fixed else VerificationState.FAILED)
        )

        return EvidenceComparisonRecord(
            finding_id=f_id,
            original_evidence=original_evidence,
            new_evidence=new_evidence,
            original_finding_summary=summary,
            current_finding_state=state,
            test_environment=test_environment,
            timestamp=datetime.now(timezone.utc),
            verification_passed=verification_passed,
            partially_fixed=partially_fixed,
            details=f"Test '{test_res.name}' result: passed={test_res.passed}. Diagnostic: {test_res.diagnostic_details}",
        )


independent_retester = IndependentRetester()
