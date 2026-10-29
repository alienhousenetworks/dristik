"""
Dristik AI Hypothesis Engine
Formulates falsifiable hypotheses regarding growth bottlenecks before deep reasoning passes,
and updates Bayesian posterior confidence as evidence is accumulated.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.orchestration.mission.state import Hypothesis
from app.domain.models import PageEvidence, Claim
from app.evidence.store import EvidenceStore

class HypothesisEngine:
    """
    Formulates and evaluates testable hypotheses against evidence.
    """

    def generate_initial_hypotheses(
        self,
        domain: str,
        pages: List[PageEvidence]
    ) -> List[Hypothesis]:
        hypotheses = [
            Hypothesis(
                id="hyp_01_conversion",
                statement="Commercial conversion friction is primarily caused by an ambiguous value proposition on first fold.",
                domain="CONVERSION",
                prior_probability=0.50,
                posterior_confidence=0.50
            ),
            Hypothesis(
                id="hyp_02_trust",
                statement="Enterprise buyer bounce rate is driven by absence of verifiable trust credentials and security documentation.",
                domain="TRUST",
                prior_probability=0.45,
                posterior_confidence=0.45
            ),
            Hypothesis(
                id="hyp_03_ai_search",
                statement="AI answer engine citation readiness is constrained by missing Organization/Product Schema.org markup.",
                domain="AI_SEARCH",
                prior_probability=0.60,
                posterior_confidence=0.60
            )
        ]
        return hypotheses

    def evaluate_hypotheses_against_evidence(
        self,
        hypotheses: List[Hypothesis],
        claims: List[Claim],
        evidence_store: EvidenceStore
    ) -> List[Hypothesis]:
        """
        Updates posterior confidence for each hypothesis based on verified supporting/contradicting claims.
        """
        for hyp in hypotheses:
            supporting = []
            contradicting = []

            for claim in claims:
                stmt = claim.statement.lower()
                # Check alignment with hypothesis
                if hyp.domain == "AI_SEARCH" and ("schema" in stmt or "json-ld" in stmt or "ai" in stmt):
                    if claim.severity in ["CRITICAL", "HIGH"]:
                        supporting.append(claim.id)
                    elif claim.severity == "INFO":
                        contradicting.append(claim.id)

                elif hyp.domain == "CONVERSION" and ("value proposition" in stmt or "cta" in stmt or "messaging" in stmt):
                    if claim.severity in ["CRITICAL", "HIGH"]:
                        supporting.append(claim.id)
                    else:
                        contradicting.append(claim.id)

                elif hyp.domain == "TRUST" and ("trust" in stmt or "security" in stmt or "compliance" in stmt):
                    if claim.severity in ["CRITICAL", "HIGH"]:
                        supporting.append(claim.id)
                    else:
                        contradicting.append(claim.id)

            hyp.supporting_evidence_refs = supporting
            hyp.contradicting_evidence_refs = contradicting

            # Bayesian update heuristic
            support_count = len(supporting)
            contra_count = len(contradicting)

            net_evidence = support_count - contra_count
            delta = net_evidence * 0.12
            posterior = max(0.10, min(0.95, hyp.prior_probability + delta))

            hyp.posterior_confidence = round(posterior, 2)
            if posterior >= 0.70:
                hyp.status = "validated"
            elif posterior <= 0.30:
                hyp.status = "falsified"
            else:
                hyp.status = "inconclusive"

        return hypotheses
