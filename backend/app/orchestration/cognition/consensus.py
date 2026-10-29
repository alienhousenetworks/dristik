"""
Dristik AI Consensus & Confidence Engine
Computes mathematically sound confidence scores based on evidence depth, agent agreement, and verification.
"""
from typing import List
from app.domain.models import Claim
from app.evidence.store import EvidenceStore

class ConsensusEngine:
    def calculate_confidence(self, claim: Claim, evidence_store: EvidenceStore, is_verified_by_critic: bool) -> float:
        """
        Calculates calibrated confidence:
        confidence = base_confidence * evidence_grounding_factor * critic_multiplier
        """
        base = claim.confidence
        
        # Verify that referenced evidence IDs actually exist in store
        valid_ev_count = 0
        for ev_id in claim.evidence_refs:
            if evidence_store.get(ev_id):
                valid_ev_count += 1
                
        if not claim.evidence_refs:
            # Unbacked claim gets heavily discounted
            grounding_factor = 0.50
        elif valid_ev_count == len(claim.evidence_refs):
            grounding_factor = 1.00
        else:
            grounding_factor = valid_ev_count / max(1, len(claim.evidence_refs))
            
        critic_multiplier = 1.0 if is_verified_by_critic else 0.75
        
        final_conf = base * grounding_factor * critic_multiplier
        return round(max(0.1, min(0.99, final_conf)), 2)
