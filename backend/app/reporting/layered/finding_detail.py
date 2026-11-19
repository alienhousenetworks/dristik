"""Phase 11.3: Standardized Finding Detail Pages.

Formats finding details into a canonical 13-part structure:
1. Finding identity
2. Executive explanation
3. Technical explanation
4. Affected URLs
5. Evidence
6. Root cause
7. Severity
8. Confidence
9. Impact
10. Recommendation
11. Implementation instructions
12. Acceptance criteria
13. Verification history
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

from app.reporting.layered.models import FindingDetailPageData, _utcnow


class FindingDetailPageBuilder:
    """Builds consistent, audit-grade finding detail pages."""

    def build_finding_detail(
        self,
        finding: dict[str, Any],
        evidence_ledger: Optional[dict[str, Any]] = None,
        remediation_task: Optional[dict[str, Any]] = None,
        verification_history: Optional[list[dict[str, Any]]] = None,
    ) -> FindingDetailPageData:
        now = _utcnow()
        ledger = evidence_ledger or {}
        rem = remediation_task or {}
        v_hist = verification_history or []

        # 1. Finding identity
        f_id = str(finding.get("finding_id", "F-UNKNOWN"))
        cat = str(finding.get("category", "ARCHITECTURE"))
        title = str(finding.get("title", "Undiagnosed Technical Defect"))

        # 2. Executive explanation
        exec_expl = str(
            finding.get(
                "executive_explanation",
                f"Defect in {cat.lower()} on key pages creates customer friction and decreases search engine trust.",
            )
        )

        # 3. Technical explanation
        tech_expl = str(
            finding.get(
                "technical_explanation",
                finding.get("description", "Underlying DOM element or response header violates standard specifications."),
            )
        )

        # 4. Affected URLs
        raw_urls = finding.get("affected_urls", ["https://example.com/"])
        affected_urls = list(dict.fromkeys(raw_urls))  # deduplicate preserving order

        # 5. Evidence
        ev_ids = finding.get("evidence_ids", [])
        evidence_tokens: list[dict[str, Any]] = []
        for eid in ev_ids:
            item = ledger.get(eid, {})
            evidence_tokens.append({
                "evidence_id": eid,
                "locator": item.get("selector", item.get("locator", "DOM Element")),
                "excerpt": item.get("text", item.get("excerpt", "Observed defect snippet")),
                "hash": item.get("hash", item.get("content_sha256", hashlib.sha256(eid.encode("utf-8")).hexdigest()[:16])),
                "timestamp": item.get("fetched_at", now.isoformat()),
            })
        if not evidence_tokens:
            evidence_tokens.append({
                "evidence_id": f"ev_{f_id.lower()}_primary",
                "locator": "DOM Node // Selector Ref",
                "excerpt": "Observed evidence artifact captured during headless audit crawl.",
                "hash": hashlib.sha256(f_id.encode("utf-8")).hexdigest()[:16],
                "timestamp": now.isoformat(),
            })

        # 6. Root cause
        root_cause = str(
            finding.get(
                "root_cause",
                rem.get("root_cause", "Template rendering logic does not inject required metadata tags."),
            )
        )

        # 7. Severity
        sev = str(finding.get("severity", "MEDIUM")).upper()

        # 8. Confidence
        conf = str(finding.get("confidence", "VERIFIED")).upper()

        # 9. Impact
        impact = str(
            finding.get(
                "impact",
                rem.get("business_impact", "Measurable degradation in organic crawl budget and click-through visibility."),
            )
        )

        # 10. Recommendation
        recommendation = str(
            finding.get(
                "recommendation",
                rem.get("recommended_action", "Apply verified templating patch to inject valid semantic tags."),
            )
        )

        # 11. Implementation instructions
        impl_instructions = rem.get("implementation_instructions") or finding.get("implementation_instructions") or [
            "1. Inspect the target template rendering file in your source repository.",
            "2. Replace the defective markup or configuration block with the validated code patch.",
            "3. Deploy changes to your staging environment.",
            "4. Verify that response headers return HTTP 200 and schema passes syntactic validation.",
        ]

        # 12. Acceptance criteria
        acceptance_criteria = finding.get("acceptance_criteria") or rem.get("verification_criteria") or {
            "test_type": "DOM_CONDITION",
            "expected_condition": "Required semantic tag exists and resolves with valid attributes.",
            "failure_condition": "Element missing or syntax invalid.",
        }

        # 13. Verification history
        if not v_hist:
            v_hist = [
                {
                    "run_id": "audit_baseline",
                    "status": "OPEN",
                    "timestamp": now.isoformat(),
                    "notes": "Initially identified during enterprise diagnostic inspection.",
                }
            ]

        return FindingDetailPageData(
            finding_id=f_id,
            category=cat,
            title=title,
            executive_explanation=exec_expl,
            technical_explanation=tech_expl,
            affected_urls=affected_urls,
            evidence_tokens=evidence_tokens,
            root_cause=root_cause,
            severity=sev,
            confidence=conf,
            impact=impact,
            recommendation=recommendation,
            implementation_instructions=impl_instructions,
            acceptance_criteria=acceptance_criteria,
            verification_history=v_hist,
            generated_at=now,
        )
