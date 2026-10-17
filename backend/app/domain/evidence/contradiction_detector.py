"""
Dristik AI Contradiction Detector
Detects semantic and factual conflicts between specialist agent claims.

v4: DOM vs external (ext_xxx) conflicts are CONTESTED and must NOT be
auto-resolved here. They are routed to verification.contradiction.v3.
"""
from typing import List
from app.domain.enums import SourceIntegrityLabel, VerificationStatus
from app.domain.models import Claim, Contradiction

CONTRADICTION_AGENT_ID = "verification.contradiction.v3"


class ContradictionDetector:
    def detect_contradictions(self, claims: List[Claim]) -> List[Contradiction]:
        contradictions: List[Contradiction] = []
        c_counter = 0

        for claim in claims:
            if (
                claim.source_integrity_label == SourceIntegrityLabel.CONTESTED
                or claim.verification_status == VerificationStatus.CONTESTED
            ):
                c_counter += 1
                contradictions.append(Contradiction(
                    id=f"contra_{c_counter:03d}",
                    claim_a_id=claim.id,
                    claim_b_id=claim.id,
                    description=(
                        f"External ground-truth feed contradicts DOM evidence for "
                        f"{claim.claim_family.value if claim.claim_family else 'gated claim'} "
                        f"({claim.id}). Tokens: {claim.evidence_refs}."
                    ),
                    resolution=f"ROUTED_TO_{CONTRADICTION_AGENT_ID}",
                    winner_claim_id=None,
                    routed_to=CONTRADICTION_AGENT_ID,
                ))

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                if c1.verification_status == VerificationStatus.CONTESTED or c2.verification_status == VerificationStatus.CONTESTED:
                    continue
                if c1.source_integrity_label == SourceIntegrityLabel.CONTESTED or c2.source_integrity_label == SourceIntegrityLabel.CONTESTED:
                    continue

                if c1.category == c2.category:
                    s1 = c1.statement.lower()
                    s2 = c2.statement.lower()

                    is_conflict = False
                    reason = ""

                    if ("has valid schema" in s1 or "schema found" in s1) and ("missing schema" in s2 or "no schema" in s2):
                        is_conflict = True
                        reason = "Conflict regarding presence of structured JSON-LD schema."
                    elif ("fast" in s1 or "good performance" in s1) and ("slow" in s2 or "poor performance" in s2):
                        is_conflict = True
                        reason = "Conflict regarding website speed and server TTFB performance."
                    elif ("clear cta" in s1) and ("missing cta" in s2 or "unclear cta" in s2):
                        is_conflict = True
                        reason = "Conflict regarding clarity of primary call-to-action."

                    if is_conflict:
                        c_counter += 1
                        winner = c1.id if len(c1.evidence_refs) >= len(c2.evidence_refs) else c2.id
                        contradictions.append(Contradiction(
                            id=f"contra_{c_counter:03d}",
                            claim_a_id=c1.id,
                            claim_b_id=c2.id,
                            description=reason,
                            resolution=f"Resolved by prioritizing claim {winner} with higher evidence grounding.",
                            winner_claim_id=winner,
                        ))

        return contradictions
