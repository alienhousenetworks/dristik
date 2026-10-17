"""Project an existing audit report into Discover, Decide, Execute, and Prove.

The projection keeps every finding. It does not drop SEO, GEO, AEO, CRO,
authority, or conversion coverage.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from app.commercial.outcomes import attribution_layers_from_channels, verification_layers_for_check
from app.commercial.remediation_policy import deployment_decision


_SEVERITY = {"CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "INFO": 1}


def _rank(finding: dict[str, Any]) -> tuple:
    calibrated = finding.get("calibrated_impact") or {}
    business = _SEVERITY.get(str(calibrated.get("business_impact") or "").upper(), 0)
    if business == 0:
        business = int(finding.get("impact") or 0)
    confidence = calibrated.get("confidence")
    if confidence is None:
        confidence = finding.get("confidence") or 0
    effort = int(finding.get("effort") or 5)
    severity = _SEVERITY.get(str(finding.get("severity") or "").upper(), 0)
    return (business, float(confidence), -effort, severity)


def _enum(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    return value


def project_operating_workflow(report: Optional[dict[str, Any]]) -> dict[str, Any]:
    report = report or {}
    findings = [item for item in (report.get("findings") or []) if isinstance(item, dict)]
    ranked = sorted(findings, key=_rank, reverse=True)
    patches = list(report.get("remediation_patches") or []) + list(report.get("code_patches") or [])
    visibility = report.get("ai_visibility_scorecard") or {}
    crawl = report.get("crawl_summary") or {}
    pages = ((report.get("crawl_manifest") or {}).get("pages") or []) if isinstance(report.get("crawl_manifest"), dict) else []
    technical_statuses = [
        str((item.get("remediation_verification") or {}).get("status") or item.get("resolution_status") or "OPEN")
        for item in findings
    ]
    resolved = sum(1 for status in technical_statuses if status in {"RESOLVED", "VERIFIED"})
    return {
        "promise": ["discover", "diagnose", "prioritize", "fix", "verify", "attribute"],
        "existing_coverage_retained": ["seo", "geo", "aeo", "cro", "authority", "conversion"],
        "discover": {
            "title": "Brand Intelligence",
            "domain": report.get("domain") or report.get("website_url"),
            "website_url": report.get("website_url"),
            "generated_at": report.get("generated_at"),
            "crawl_summary": crawl,
            "pages_in_manifest": len(pages) if isinstance(pages, list) else None,
            "scores_present": sorted((report.get("scores") or {}).keys()) if isinstance(report.get("scores"), dict) else [],
            "ai_visibility": {
                "status": visibility.get("status") or "not_measured",
                "successful_runs": visibility.get("successful_runs"),
                "failed_runs": visibility.get("failed_runs"),
                "queries": visibility.get("queries"),
                "repeats": visibility.get("repeats"),
                "mention_rate_pct": visibility.get("mention_rate_pct"),
                "citation_rate_pct": visibility.get("citation_rate_pct"),
                "not_measured_reason": visibility.get("not_measured_reason"),
                "measurement_note": visibility.get("measurement_note"),
                "combined_into_single_score": False,
            },
            "external_authority_attached": bool(report.get("external_authority")),
            "google_performance": report.get("google_performance"),
        },
        "decide": {
            "title": "Prioritized Opportunity Center",
            "ranking": "business impact, confidence, lower effort, then technical severity",
            "findings": [
                {
                    "finding_id": item.get("finding_id"),
                    "title": item.get("title"),
                    "category": _enum(item.get("category")),
                    "severity": _enum(item.get("severity")),
                    "confidence": (item.get("calibrated_impact") or {}).get("confidence", item.get("confidence")),
                    "confidence_label": item.get("confidence_label"),
                    "effort": item.get("effort"),
                    "evidence_scope": item.get("evidence_scope"),
                    "evidence_refs": item.get("evidence_refs") or [],
                    "business_impact": (item.get("calibrated_impact") or {}).get("business_impact") or item.get("business_impact"),
                    "recommendation": item.get("recommendation"),
                }
                for item in ranked
            ],
        },
        "execute": {
            "title": "Remediation Workspace",
            "patches": [
                {
                    "patch_id": item.get("patch_id"),
                    "title": item.get("title"),
                    "finding_id": item.get("finding_id"),
                    "approval_status": _enum(item.get("approval_status") or item.get("release_status")),
                    "risk_level": _enum(item.get("risk_level")),
                    "pr_url": item.get("pr_url"),
                    "policy": deployment_decision(SimpleNamespace(**item)),
                }
                for item in patches
                if isinstance(item, dict)
            ],
            "rule": (
                "Preview the diff, require approval for consequential changes, "
                "and do not let an agent deploy to production without an explicit authorization."
            ),
        },
        "prove": {
            "title": "Impact and Evidence Center",
            "technical_findings_resolved": resolved,
            "technical_findings_total": len(findings),
            "verification_layers": [
                layer.model_dump()
                for layer in verification_layers_for_check(
                    technical_status="partial" if resolved and resolved < len(findings) else (
                        "condition_resolved" if resolved and resolved == len(findings) and findings else "not_measured"
                    ),
                    visibility_measured=visibility.get("status") == "MEASURED" and visibility.get("successful_runs") not in (None, 0),
                    visibility_summary=(
                        "This run has live visibility observations. They are not a before-and-after of a specific patch "
                        "unless a later measurement uses the same prompt panel."
                        if visibility.get("successful_runs")
                        else "No live AI visibility measurement is attached to this audit."
                    ),
                )
            ],
            "attribution_layers": [layer.model_dump() for layer in attribution_layers_from_channels(report.get("google_performance"))],
            "score_increase_is_not_attribution": True,
        },
    }
