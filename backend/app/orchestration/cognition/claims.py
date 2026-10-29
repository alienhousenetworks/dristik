"""
Dristik AI Claim Registry
Tracks proposed agent claims, evidence provenance links, verification status, and contradictions.
"""
from typing import Dict, List, Optional, Any
from app.domain.models import Claim, Contradiction
from app.domain.enums import VerificationStatus, Severity, Category, ClaimType

class ClaimRegistry:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self._claims: Dict[str, Claim] = {}
        self._contradictions: List[Contradiction] = []
        self._counter: int = 0
        self._contra_counter: int = 0

    def add_claim(self, claim: Claim) -> Claim:
        if not getattr(claim, "id", None):
            self._counter += 1
            claim.id = f"claim_{self._counter:03d}"
        self._claims[claim.id] = claim
        return claim

    def register_claim(
        self,
        agent_id: Any,
        statement: Optional[str] = None,
        category: Optional[Category] = None,
        severity: Severity = Severity.MEDIUM,
        claim_type: ClaimType = ClaimType.FACT,
        evidence_refs: Optional[List[str]] = None,
        confidence: float = 0.85,
        recommendation: Optional[str] = None,
        impact: int = 5,
        effort: int = 5,
        evidence_level: Optional[Any] = None,
        observation_type: Optional[Any] = None,
        provenance_hash: Optional[str] = None
    ) -> Claim:
        if isinstance(agent_id, Claim):
            return self.add_claim(agent_id)
        if isinstance(agent_id, dict):
            try:
                return self.add_claim(Claim(**agent_id))
            except Exception:
                pass
        self._counter += 1
        claim_id = f"claim_{self._counter:03d}"
        
        claim = Claim(
            id=claim_id,
            agent_id=agent_id,
            statement=statement,
            claim_type=claim_type,
            category=category,
            severity=severity,
            evidence_refs=evidence_refs or [],
            supporting_agents=[agent_id],
            contradicting_agents=[],
            confidence=confidence,
            verification_status=VerificationStatus.PROVISIONAL,
            recommendation=recommendation,
            impact=impact,
            effort=effort,
            provenance_hash=provenance_hash
        )
        if evidence_level is not None:
            claim.evidence_level = evidence_level
        if observation_type is not None:
            claim.observation_type = observation_type
            
        self._claims[claim_id] = claim
        return claim

    def register_contradiction(
        self,
        claim_a_id: str,
        claim_b_id: str,
        description: str,
        resolution: str,
        winner_claim_id: Optional[str] = None,
        routed_to: Optional[str] = None,
        **_ignored
    ) -> Contradiction:
        self._contra_counter += 1
        contra_id = f"contra_{self._contra_counter:03d}"
        contra = Contradiction(
            id=contra_id,
            claim_a_id=claim_a_id,
            claim_b_id=claim_b_id,
            description=description,
            resolution=resolution,
            winner_claim_id=winner_claim_id,
            routed_to=routed_to,
        )
        self._contradictions.append(contra)
        return contra

    def get(self, claim_id: str) -> Optional[Claim]:
        return self._claims.get(claim_id)

    def get_all(self) -> List[Claim]:
        return list(self._claims.values())

    def get_verified(self) -> List[Claim]:
        return [c for c in self._claims.values() if c.verification_status == VerificationStatus.VERIFIED]

    def get_by_category(self, category: Category) -> List[Claim]:
        return [c for c in self._claims.values() if c.category == category]

    def get_contradictions(self) -> List[Contradiction]:
        return self._contradictions

    def update_status(self, claim_id: str, status: VerificationStatus, notes: Optional[str] = None, adjusted_confidence: Optional[float] = None) -> Optional[Claim]:
        claim = self._claims.get(claim_id)
        if claim:
            claim.verification_status = status
            if notes:
                claim.verification_notes = notes
            if adjusted_confidence is not None:
                claim.confidence = adjusted_confidence
        return claim

    def advance_claim_state(
        self,
        claim_id: str,
        new_state: Any,
        new_status: Optional[VerificationStatus] = None,
        notes: Optional[str] = None,
        adjusted_confidence: Optional[float] = None
    ) -> Optional[Claim]:
        """Advance claim through zero-hallucination state machine."""
        claim = self._claims.get(claim_id)
        if claim:
            claim.claim_state = new_state
            if new_status:
                claim.verification_status = new_status
            if notes:
                claim.verification_notes = notes
            if adjusted_confidence is not None:
                claim.confidence = adjusted_confidence
        return claim
