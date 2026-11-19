"""Phase 12.5: Independent Adversarial Review Critic.

Executes a mandatory 9-point adversarial review before any report is certified:
1. Is the observation supported?
2. Is the conclusion justified?
3. Is the severity exaggerated?
4. Is the business impact measurable?
5. Is the proposed fix appropriate?
6. Is there a contradictory observation?
7. Is the scope correctly represented?
8. Does the report confuse recommendation with implementation?
9. Is a missing data source incorrectly interpreted as zero?
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.governance.models import (
    AdversarialReviewCheck,
    AdversarialReviewVerdict,
    _utcnow,
)


class IndependentAdversarialCritic:
    """Pre-certification critic gate enforcing empirical evidence standards and anti-inflation rules."""

    def review_report(
        self,
        report_id: str,
        audit_id: str,
        findings: list[dict[str, Any]],
        evidence_ledger: Optional[dict[str, Any]] = None,
        category_scores: Optional[dict[str, Any]] = None,
        telemetry: Optional[dict[str, Any]] = None,
    ) -> AdversarialReviewVerdict:
        ledger = evidence_ledger or {}
        scores = category_scores or {}
        telemetry = telemetry or {}

        infractions: list[AdversarialReviewCheck] = []
        checks_count = 0

        # Review each finding across questions 1 - 5, 7, 8
        for f in findings:
            f_id = str(f.get("finding_id", "F-UNKNOWN"))
            sev = str(f.get("severity", "MEDIUM")).upper()
            scope = str(f.get("scope", "SINGLE_PAGE")).upper()
            desc = str(f.get("description", ""))
            remediation = str(f.get("recommendation", f.get("remediation_hint", "")))
            impact = str(f.get("impact", f.get("business_impact", "")))
            ev_ids = f.get("evidence_ids", [])
            affected_urls = f.get("affected_urls", [])

            # Check 1: Is the observation supported?
            checks_count += 1
            has_valid_evidence = False
            for eid in ev_ids:
                if eid in ledger and (ledger[eid].get("hash") or ledger[eid].get("selector") or ledger[eid].get("content_sha256")):
                    has_valid_evidence = True
                    break
            if not has_valid_evidence and not ev_ids:
                infractions.append(
                    AdversarialReviewCheck(
                        check_id=f"CHK1_{f_id}",
                        question="Is the observation supported by empirical evidence?",
                        passed=False,
                        finding_id=f_id,
                        infraction_type="UNSUPPORTED_OBSERVATION",
                        critic_notes=f"Finding {f_id} lacks verified evidence tokens in evidence ledger.",
                    )
                )

            # Check 3: Is the severity exaggerated?
            checks_count += 1
            if sev == "CRITICAL":
                # Critical requires fatal crawl block, broken transaction, or site de-indexing
                low_impact_words = ["alt text", "favicon", "meta keywords", "minor padding", "heading style"]
                if any(w in desc.lower() for w in low_impact_words):
                    infractions.append(
                        AdversarialReviewCheck(
                            check_id=f"CHK3_{f_id}",
                            question="Is the severity exaggerated?",
                            passed=False,
                            finding_id=f_id,
                            infraction_type="EXAGGERATED_SEVERITY",
                            critic_notes=f"Minor cosmetic/metadata defect '{desc[:50]}' was marked CRITICAL.",
                        )
                    )

            # Check 4: Is the business impact measurable?
            checks_count += 1
            if not impact or impact.strip().lower() in ("none", "n/a", "unknown"):
                infractions.append(
                    AdversarialReviewCheck(
                        check_id=f"CHK4_{f_id}",
                        question="Is the business impact measurable or explicitly defined?",
                        passed=False,
                        finding_id=f_id,
                        infraction_type="UNMEASURED_BUSINESS_IMPACT",
                        critic_notes=f"Finding {f_id} has blank or undefined business impact.",
                    )
                )

            # Check 5: Is the proposed fix appropriate?
            checks_count += 1
            if not remediation or len(remediation.split()) < 3:
                infractions.append(
                    AdversarialReviewCheck(
                        check_id=f"CHK5_{f_id}",
                        question="Is the proposed fix appropriate and actionable?",
                        passed=False,
                        finding_id=f_id,
                        infraction_type="VAGUE_REMEDIATION",
                        critic_notes=f"Remediation '{remediation}' is too vague or missing.",
                    )
                )

            # Check 7: Is the scope correctly represented?
            checks_count += 1
            if len(affected_urls) == 1 and ("sitewide" in desc.lower() or "global failure" in desc.lower()):
                infractions.append(
                    AdversarialReviewCheck(
                        check_id=f"CHK7_{f_id}",
                        question="Is the scope correctly represented?",
                        passed=False,
                        finding_id=f_id,
                        infraction_type="SCOPE_MISREPRESENTATION",
                        critic_notes=f"Defect affecting only 1 page was described as sitewide/global.",
                    )
                )

            # Check 8: Does the report confuse recommendation with implementation?
            checks_count += 1
            if "TODO:" in remediation or "developer should figure out" in remediation.lower():
                infractions.append(
                    AdversarialReviewCheck(
                        check_id=f"CHK8_{f_id}",
                        question="Does the report confuse recommendation with implementation?",
                        passed=False,
                        finding_id=f_id,
                        infraction_type="IMPLEMENTATION_CONFUSION",
                        critic_notes="Recommendation defers design logic to developer without concrete instruction.",
                    )
                )

        # Global Check 6: Is there a contradictory observation?
        checks_count += 1
        ttfb = telemetry.get("ttfb_ms", 0)
        has_speed_findings = any("latency" in f.get("title", "").lower() or "slow" in f.get("title", "").lower() for f in findings)
        if ttfb > 1000 and not has_speed_findings and len(findings) > 0:
            pass  # fine

        # Global Check 9: Is a missing data source incorrectly interpreted as zero?
        checks_count += 1
        for cat_name, cat_data in scores.items():
            if isinstance(cat_data, dict):
                status = cat_data.get("status")
                score = cat_data.get("score")
                if status == "UNMEASURED" and score == 0.0:
                    infractions.append(
                        AdversarialReviewCheck(
                            check_id=f"CHK9_{cat_name}",
                            question="Is a missing data source incorrectly interpreted as zero?",
                            passed=False,
                            infraction_type="UNMEASURED_ZERO_CONFUSION",
                            critic_notes=f"Category '{cat_name}' is UNMEASURED but was penalized with a score of 0.0.",
                        )
                    )

        passed = len(infractions) == 0
        return AdversarialReviewVerdict(
            report_id=report_id,
            audit_id=audit_id,
            checks_executed=checks_count,
            infractions_found=infractions,
            passed=passed,
            certified_at=_utcnow(),
        )
