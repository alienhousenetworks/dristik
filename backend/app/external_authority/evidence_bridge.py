"""Map external findings into the existing evidence store and Finding model."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.enums import Category, EvidenceClass, EvidenceState, FindingClassification, Severity
from app.domain.models import Finding, FindingEvidence


def to_domain_findings(findings: List[Dict[str, Any]], *, include_gaps: bool = False) -> List[Finding]:
    selected = []
    for item in findings:
        gap = item.get("data_state") in {"NOT_CONNECTED", "NOT_APPLICABLE", "UNAVAILABLE"} or item.get("severity") == "INFO"
        if gap and not include_gaps:
            continue
        selected.append(_one(item))
    return selected


def record_evidence(evidence_store: Any, findings: List[Dict[str, Any]]) -> int:
    if evidence_store is None:
        return 0
    written = 0
    for item in findings:
        evidence_store.add_evidence(
            source_type="external",
            analyzer="external_authority",
            url=item.get("evidence_url"),
            text=item.get("title"),
            value={
                "metric": item.get("metric"),
                "observed_value": item.get("observed_value"),
                "previous_value": item.get("previous_value"),
                "provider": item.get("provider"),
                "evidence_basis": item.get("evidence_basis"),
                "period": item.get("period"),
                "data_state": item.get("data_state"),
                "scope": item.get("scope"),
            },
            metadata={
                "pillar": item.get("pillar"),
                "provider": item.get("provider"),
                "verification_method": item.get("verification_method"),
                "vendor_metric_label": item.get("vendor_metric_label"),
            },
        )
        written += 1
    return written


def _one(item: Dict[str, Any]) -> Finding:
    basis = item.get("evidence_basis")
    if item.get("data_state") in {"NOT_CONNECTED", "NOT_APPLICABLE", "UNAVAILABLE"}:
        classification = FindingClassification.INSUFFICIENT_DATA
        evidence_class = EvidenceClass.HYPOTHESIS
        state = EvidenceState.UNAVAILABLE
    elif basis == "DIRECT_PROVIDER_EVIDENCE":
        classification = FindingClassification.VERIFIED_DEFECT if item.get("severity") in {"HIGH", "CRITICAL", "MEDIUM"} else FindingClassification.VERIFIED_OPPORTUNITY
        evidence_class = EvidenceClass.EXTERNALLY_VERIFIED
        state = EvidenceState.OBSERVED
    elif basis == "INFERRED":
        classification = FindingClassification.VERIFIED_OPPORTUNITY
        evidence_class = EvidenceClass.MODEL_INFERRED
        state = EvidenceState.INFERRED
    else:
        classification = FindingClassification.INSUFFICIENT_DATA
        evidence_class = EvidenceClass.HYPOTHESIS
        state = EvidenceState.UNAVAILABLE
    return Finding(
        finding_id=item["finding_id"],
        category=Category.EXTERNAL_AUTHORITY,
        severity=Severity(item.get("severity") or "INFO"),
        classification=classification,
        title=item.get("title") or "External measurement",
        description=item.get("description") or "",
        recommendation=item.get("recommendation") or "",
        confidence=float(item.get("confidence") or 0.5),
        evidence_scope=item.get("scope"),
        evidence_class=evidence_class,
        evidence_subtype="SEARCH",
        business_impact=item.get("impact"),
        why_it_matters=item.get("impact"),
        verification_notes=item.get("verification_method"),
        held_from_executive=item.get("severity") == "INFO" or item.get("data_state") in {"NOT_CONNECTED", "NOT_APPLICABLE"},
        evidence=[
            FindingEvidence(
                url=item.get("evidence_url"),
                element="external_provider",
                value=str(item.get("observed_value")),
                snippet=item.get("title"),
                source=item.get("provider"),
                type="external",
                state=state,
                evidence_class=evidence_class,
                evidence_subtype="SEARCH",
            )
        ],
    )
