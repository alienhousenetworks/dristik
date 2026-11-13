"""
Dristik AI Hypothesis Engine
Formulates falsifiable hypotheses regarding growth bottlenecks before deep reasoning passes,
and updates Bayesian posterior confidence as evidence is accumulated.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.orchestration.mission.state import Hypothesis
from app.domain.models import PageEvidence, Claim, Finding, HypothesisMatrixItem
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

    def build_hypotheses_matrix(
        self,
        hypotheses: List[Hypothesis],
        claims: List[Claim],
        exploratory_hypotheses: Optional[List[Finding]] = None,
        google_performance: Optional[Dict[str, Any]] = None,
    ) -> List[HypothesisMatrixItem]:
        """Build a unified, UI-ready Hypotheses Matrix from Bayesian hypotheses and exploratory findings."""
        claim_by_id = {c.id: c for c in claims}
        telemetry_defaults = {
            "CONVERSION": ["GA4 Conversion Funnels", "Above-the-Fold CTA Telemetry"],
            "TRUST": ["Security & Compliance Docs", "External Authority Signals"],
            "AI_SEARCH": ["Schema.org JSON-LD AST", "AI Answer Engine Probes"],
        }
        action_defaults = {
            "CONVERSION": "Run A/B hero value-proposition test and verify CTA click-through in GA4.",
            "TRUST": "Publish verifiable SOC2/security credentials and surface customer proof on key landing pages.",
            "AI_SEARCH": "Deploy Organization & Product JSON-LD and validate AI citation pickup.",
        }

        items: List[HypothesisMatrixItem] = []
        for hyp in hypotheses:
            support_summaries = [
                claim_by_id[cid].statement for cid in hyp.supporting_evidence_refs if cid in claim_by_id
            ][:5]
            contra_summaries = [
                claim_by_id[cid].statement for cid in hyp.contradicting_evidence_refs if cid in claim_by_id
            ][:5]
            delta = round(hyp.posterior_confidence - hyp.prior_probability, 2)
            items.append(
                HypothesisMatrixItem(
                    id=hyp.id,
                    statement=hyp.statement,
                    domain=hyp.domain,
                    source="bayesian_engine",
                    prior_probability=hyp.prior_probability,
                    posterior_confidence=hyp.posterior_confidence,
                    confidence_delta=delta,
                    status=hyp.status,
                    supporting_evidence_refs=list(hyp.supporting_evidence_refs),
                    contradicting_evidence_refs=list(hyp.contradicting_evidence_refs),
                    supporting_summaries=support_summaries,
                    contradicting_summaries=contra_summaries,
                    required_telemetry=telemetry_defaults.get(hyp.domain, ["First-Party Telemetry"]),
                    recommended_action=action_defaults.get(hyp.domain),
                )
            )

        # Include unverified / exploratory hypothesis findings (avoiding duplicate IDs)
        seen_ids = {item.id for item in items}
        gsc_connected = bool((google_performance or {}).get("search_console", {}).get("state") == "CONNECTED")
        ga4_connected = bool((google_performance or {}).get("analytics", {}).get("state") == "CONNECTED")

        for finding in exploratory_hypotheses or []:
            fid = finding.id or f"exp_{len(items) + 1}"
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            conf = round(float(getattr(finding, "confidence", 0.40) or 0.40), 2)
            domain_label = getattr(finding.category, "value", str(finding.category)).upper()
            req_tel: List[str] = []
            if not gsc_connected:
                req_tel.append("Google Search Console")
            if not ga4_connected:
                req_tel.append("Google Analytics 4")
            if not req_tel:
                req_tel.append("Manual SME / Production Verification")

            items.append(
                HypothesisMatrixItem(
                    id=fid,
                    statement=finding.title or finding.description or "Exploratory hypothesis",
                    domain=domain_label,
                    source="exploratory_finding",
                    prior_probability=0.50,
                    posterior_confidence=conf,
                    confidence_delta=round(conf - 0.50, 2),
                    status="validated" if conf >= 0.70 else "falsified" if conf <= 0.30 else "inconclusive",
                    supporting_evidence_refs=list(getattr(finding, "evidence_refs", []) or []),
                    contradicting_evidence_refs=[],
                    supporting_summaries=[finding.description] if finding.description else [],
                    contradicting_summaries=[],
                    required_telemetry=req_tel,
                    recommended_action=finding.recommendation or getattr(finding, "verification_method", None),
                )
            )

        return items
