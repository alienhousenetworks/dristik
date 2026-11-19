"""Phase 10.3: Finding Lifecycle Monitoring.

Tracks finding evolution across audits:
- New findings
- Resolved findings
- Reopened findings (previously marked resolved/verified, but re-detected)
- Recurring findings (detected in >= 3 audits)
- Severity changes (escalated or downgraded)
- Affected page changes (expanded or contracted URL scope)
- Unresolved remediation tasks
"""
from __future__ import annotations

from typing import Any, Optional

from app.monitoring.models import (
    FindingLifecycleDiff,
    FindingLifecycleRecord,
    FindingLifecycleState,
    _utcnow,
)


class FindingLifecycleMonitor:
    """Tracks finding transitions, recurrences, and severity shifts across audit runs."""

    def __init__(self, recurring_threshold: int = 3):
        self.recurring_threshold = recurring_threshold

    def evaluate_lifecycle(
        self,
        domain: str,
        baseline_audit_id: str,
        current_audit_id: str,
        baseline_findings: list[dict[str, Any]],
        current_findings: list[dict[str, Any]],
        historical_resolved_ids: Optional[set[str]] = None,
        historical_occurrence_counts: Optional[dict[str, int]] = None,
        unresolved_remediation_tasks: Optional[list[str]] = None,
    ) -> FindingLifecycleDiff:
        hist_resolved = historical_resolved_ids or set()
        hist_counts = dict(historical_occurrence_counts or {})
        unresolved_tasks = list(unresolved_remediation_tasks or [])

        b_map = {f["finding_id"]: f for f in baseline_findings if "finding_id" in f}
        c_map = {f["finding_id"]: f for f in current_findings if "finding_id" in f}

        b_ids = set(b_map.keys())
        c_ids = set(c_map.keys())

        new_ids = c_ids - b_ids
        resolved_ids = b_ids - c_ids
        persisting_ids = b_ids & c_ids

        diff = FindingLifecycleDiff(
            domain=domain,
            baseline_audit_id=baseline_audit_id,
            current_audit_id=current_audit_id,
            unresolved_remediation_tasks=unresolved_tasks,
            generated_at=_utcnow(),
        )

        # 1. New or Reopened findings
        for f_id in sorted(list(new_ids)):
            c_f = c_map[f_id]
            curr_sev = c_f.get("severity", "MEDIUM")
            curr_urls = c_f.get("affected_urls", [])
            past_occurrences = hist_counts.get(f_id, 0) + 1
            hist_counts[f_id] = past_occurrences

            if f_id in hist_resolved:
                rec = FindingLifecycleRecord(
                    finding_id=f_id,
                    state=FindingLifecycleState.REOPENED,
                    previous_severity=c_f.get("previous_severity"),
                    current_severity=curr_sev,
                    current_urls=curr_urls,
                    audit_occurrence_count=past_occurrences,
                    details="Finding was previously resolved but re-detected in current audit run.",
                )
                diff.reopened_findings.append(rec)
            else:
                rec = FindingLifecycleRecord(
                    finding_id=f_id,
                    state=FindingLifecycleState.NEW,
                    current_severity=curr_sev,
                    current_urls=curr_urls,
                    audit_occurrence_count=past_occurrences,
                    details="Newly discovered finding in current audit run.",
                )
                diff.new_findings.append(rec)

        # 2. Resolved findings
        for f_id in sorted(list(resolved_ids)):
            b_f = b_map[f_id]
            rec = FindingLifecycleRecord(
                finding_id=f_id,
                state=FindingLifecycleState.RESOLVED,
                previous_severity=b_f.get("severity"),
                current_severity=None,
                previous_urls=b_f.get("affected_urls", []),
                audit_occurrence_count=hist_counts.get(f_id, 1),
                details="Finding was present in baseline audit but no longer detected in current audit.",
            )
            diff.resolved_findings.append(rec)

        # 3. Persisting findings: check severity, affected URLs, recurring
        for f_id in sorted(list(persisting_ids)):
            b_f = b_map[f_id]
            c_f = c_map[f_id]
            b_sev = b_f.get("severity", "MEDIUM")
            c_sev = c_f.get("severity", "MEDIUM")
            b_urls = sorted(b_f.get("affected_urls", []))
            c_urls = sorted(c_f.get("affected_urls", []))
            past_occurrences = hist_counts.get(f_id, 1) + 1
            hist_counts[f_id] = past_occurrences

            # Recurring defect check (>= threshold)
            if past_occurrences >= self.recurring_threshold:
                diff.recurring_findings.append(
                    FindingLifecycleRecord(
                        finding_id=f_id,
                        state=FindingLifecycleState.RECURRING,
                        previous_severity=b_sev,
                        current_severity=c_sev,
                        previous_urls=b_urls,
                        current_urls=c_urls,
                        audit_occurrence_count=past_occurrences,
                        details=f"Persistent recurring defect observed across {past_occurrences} consecutive audits.",
                    )
                )

            # Severity change check
            if b_sev != c_sev:
                diff.severity_changes.append(
                    FindingLifecycleRecord(
                        finding_id=f_id,
                        state=FindingLifecycleState.SEVERITY_CHANGED,
                        previous_severity=b_sev,
                        current_severity=c_sev,
                        previous_urls=b_urls,
                        current_urls=c_urls,
                        audit_occurrence_count=past_occurrences,
                        details=f"Severity transitioned from {b_sev} to {c_sev}.",
                    )
                )

            # Affected pages change check
            if b_urls != c_urls:
                diff.affected_page_changes.append(
                    FindingLifecycleRecord(
                        finding_id=f_id,
                        state=FindingLifecycleState.AFFECTED_PAGES_CHANGED,
                        previous_severity=b_sev,
                        current_severity=c_sev,
                        previous_urls=b_urls,
                        current_urls=c_urls,
                        audit_occurrence_count=past_occurrences,
                        details=f"Affected URL scope changed from {len(b_urls)} to {len(c_urls)} pages.",
                    )
                )

        return diff
