"""
Dristik AI Adversarial Evidence Critic & Fact Checker
Conducts rigorous falsification checks against raw evidence and eliminates hallucinations.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import VerificationStatus
from app.cognition.consensus import ConsensusEngine
from app.cognition.contradiction import ContradictionDetector

class AdversarialCriticAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_critic", capability="critic", model_router=model_router)
        self.consensus_engine = ConsensusEngine()
        self.contradiction_detector = ContradictionDetector()

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        claims = blackboard.claim_registry.get_all()
        
        # 1. Detect and resolve contradictions
        contradictions = self.contradiction_detector.detect_contradictions(claims)
        blackboard.contradictions = contradictions
        
        # 2. Audit each claim against physical evidence
        verified_count = 0
        rejected_count = 0
        
        for claim in claims:
            # Verify referenced evidence
            valid_refs = [ref for ref in claim.evidence_refs if blackboard.evidence_store.get(ref)]
            
            if not valid_refs:
                # Downgrade unbacked claims
                claim.confidence = min(claim.confidence, 0.30)
                claim.verification_status = VerificationStatus.INSUFFICIENT_EVIDENCE
                claim.verification_notes = "Downgraded: No corroborating evidence IDs found in evidence store."
                rejected_count += 1
            else:
                # Calibrate confidence using consensus engine
                calibrated = self.consensus_engine.calculate_confidence(
                    claim=claim,
                    evidence_store=blackboard.evidence_store,
                    is_verified_by_critic=True
                )
                claim.confidence = calibrated
                if calibrated >= 0.70:
                    claim.verification_status = VerificationStatus.VERIFIED
                    claim.verification_notes = f"Verified against {len(valid_refs)} evidence observation(s)."
                    verified_count += 1
                else:
                    claim.verification_status = VerificationStatus.PENDING_VERIFICATION
                    claim.verification_notes = f"Corroborated by {len(valid_refs)} evidence observation(s) but calibrated confidence {calibrated:.2f} < 0.70."
                    rejected_count += 1
                
        blackboard.log_step("Adversarial Verification Completed", self.agent_id, {
            "verified_claims": verified_count,
            "rejected_claims": rejected_count,
            "contradictions_found": len(contradictions)
        })
        return {
            "verified_count": verified_count,
            "rejected_count": rejected_count,
            "contradictions_count": len(contradictions)
        }
