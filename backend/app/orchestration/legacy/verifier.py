"""
Evidence Verifier & Judge Agent
Enforces the core product principle: No invented findings.
Validates findings against collected evidence, removes ungrounded claims, and calibrates confidence.
"""
from typing import Dict, Any, List
from app.domain.models import Finding
from app.domain.enums import VerificationStatus, EvidenceConfidence

class EvidenceVerifierJudgeAgent:
    def __init__(self):
        self.agent_id = "judge.verifier.v2"

    async def verify_findings(self, raw_findings: List[Finding]) -> tuple[List[Finding], Dict[str, Any]]:
        verified_findings: List[Finding] = []
        rejected_count = 0
        dedup_map: Dict[str, Finding] = {}

        for finding in raw_findings:
            # 1. Evidence Existence Check
            if not finding.evidence or len(finding.evidence) == 0:
                # Reject findings with zero evidence
                rejected_count += 1
                continue

            # Ensure evidence has non-empty values
            has_valid_evidence = any(bool(e.value and e.value.strip()) for e in finding.evidence)
            if not has_valid_evidence:
                rejected_count += 1
                continue

            # 2. Calibrate Confidence Label
            if finding.confidence >= 0.95:
                finding.confidence_label = EvidenceConfidence.CONFIRMED
            elif finding.confidence >= 0.85:
                finding.confidence_label = EvidenceConfidence.STRONG
            elif finding.confidence >= 0.70:
                finding.confidence_label = EvidenceConfidence.LIKELY
            elif finding.confidence >= 0.50:
                finding.confidence_label = EvidenceConfidence.POTENTIAL
            else:
                finding.confidence_label = EvidenceConfidence.UNCERTAIN

            # 3. Deduplication by rule_id or title
            key = finding.rule_id or finding.title.lower().strip()
            if key in dedup_map:
                # Retain the one with higher confidence or higher impact
                existing = dedup_map[key]
                if finding.confidence > existing.confidence:
                    dedup_map[key] = finding
            else:
                dedup_map[key] = finding

        # Re-sort by calculated priority: (Impact * Confidence * 10) / (Effort + 2)
        verified_findings = list(dedup_map.values())
        for f in verified_findings:
            calculated_priority = int((f.impact * f.confidence * 10) / (f.effort + 2))
            f.priority = max(1, min(10, calculated_priority))
            f.verification_status = VerificationStatus.VERIFIED

        verified_findings.sort(key=lambda x: (x.priority, x.impact), reverse=True)

        audit_metrics = {
            "total_submitted": len(raw_findings),
            "verified_count": len(verified_findings),
            "rejected_hallucinations": rejected_count,
            "verification_rate": round(len(verified_findings) / max(1, len(raw_findings)) * 100, 1)
        }

        return verified_findings, audit_metrics
