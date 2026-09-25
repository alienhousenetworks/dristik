"""
Dristik AI Decision Engine
Converts verified claims and observations into finalized, auditable Finding objects.
"""
from typing import List
from app.domain.models import Claim, Finding, FindingEvidence
from app.domain.enums import (
    VerificationStatus,
    EvidenceConfidence,
    Category,
    Severity,
    ConfidenceBand,
    SourceIntegrityLabel,
    RubricConfidence,
    Materiality,
)
from app.evidence.store import EvidenceStore
from app.cognition.finding_rubric import apply_rubric_to_finding

class DecisionEngine:
    def synthesize_findings(self, claims: List[Claim], evidence_store: EvidenceStore) -> List[Finding]:
        findings: List[Finding] = []
        finding_idx = 0
        
        for claim in claims:
            # Skip rejected claims
            if claim.verification_status == VerificationStatus.REJECTED:
                continue
                
            finding_idx += 1
            f_id = f"find_{finding_idx:03d}"
            
            # Map evidence references to FindingEvidence objects
            attached_ev: List[FindingEvidence] = []
            for ev_id in claim.evidence_refs:
                ev_obj = evidence_store.get(ev_id)
                if ev_obj:
                    attached_ev.append(FindingEvidence(
                        evidence_id=ev_obj.id,
                        url=ev_obj.url,
                        element=ev_obj.selector or ev_obj.source_type,
                        value=str(ev_obj.value) if ev_obj.value is not None else "",
                        selector=ev_obj.selector,
                        snippet=ev_obj.text
                    ))
                    
            # Compute confidence label. v4 HIGH/MEDIUM bands win over raw float.
            conf = claim.confidence
            if claim.confidence_band == ConfidenceBand.HIGH:
                label = EvidenceConfidence.CONFIRMED
            elif claim.confidence_band == ConfidenceBand.MEDIUM:
                label = EvidenceConfidence.LIKELY
            elif conf >= 0.95:
                label = EvidenceConfidence.CONFIRMED
            elif conf >= 0.85:
                label = EvidenceConfidence.STRONG
            elif conf >= 0.70:
                label = EvidenceConfidence.LIKELY
            elif conf >= 0.50:
                label = EvidenceConfidence.POTENTIAL
            else:
                label = EvidenceConfidence.UNCERTAIN
                
            # Causal Prioritization Model:
            # 0.30 Business Impact + 0.20 Confidence + 0.15 Reach + 0.15 Ease + 0.10 Strategic Value + 0.10 Urgency
            impact_val = float(claim.impact) # 1 - 10
            conf_val = float(claim.confidence * 10.0) # 1 - 10
            reach_val = 8.0 if claim.category in [Category.TECHNICAL_SEO, Category.ON_PAGE_SEO, Category.GEO] else 6.0
            ease_val = max(1.0, 11.0 - float(claim.effort)) # Inverse of effort
            strategic_val = 9.0 if claim.severity in [Severity.CRITICAL, Severity.HIGH] else 5.0
            urgency_val = 9.0 if claim.severity == Severity.CRITICAL else (7.0 if claim.severity == Severity.HIGH else 4.0)

            causal_score = (
                (0.30 * impact_val) +
                (0.20 * conf_val) +
                (0.15 * reach_val) +
                (0.15 * ease_val) +
                (0.10 * strategic_val) +
                (0.10 * urgency_val)
            )
            priority = max(1, min(10, round(causal_score)))
            
            finding = Finding(
                finding_id=f_id,
                category=claim.category,
                severity=claim.severity,
                title=claim.statement,
                finding=claim.statement,
                description=claim.verification_notes or claim.statement,
                evidence=attached_ev,
                evidence_refs=claim.evidence_refs,
                confidence=claim.confidence,
                confidence_label=label,
                impact=claim.impact,
                effort=claim.effort,
                priority=priority,
                recommendation=claim.recommendation or "Implement recommended architectural fix based on evidence.",
                verification_status=claim.verification_status,
                verification_notes=claim.verification_notes,
                source_integrity_label=claim.source_integrity_label or SourceIntegrityLabel.NOT_APPLICABLE,
                claim_family=claim.claim_family,
                routed_to=claim.routed_to,
                confidence_rubric=claim.confidence_rubric or RubricConfidence.LIKELY,
                confidence_basis=claim.confidence_basis or "",
                materiality=claim.materiality or Materiality.MINOR,
                source_agreement=claim.source_agreement,
                adversarial_reviewed=claim.adversarial_reviewed,
                held_from_executive=claim.held_from_executive,
            )
            apply_rubric_to_finding(finding, evidence_store)
            findings.append(finding)
            
        return findings
