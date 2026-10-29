"""
Dristik AI Adversarial Critic Worker (70B-Hardened Blind Falsification)
Audits claim atoms strictly against referenced evidence slices without author rationale,
copy rewrites, or financial models. Computes confidence calibration deterministically in code.
"""
import json
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import VerificationStatus, Severity
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import CriticOutput

class CognitiveCriticWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(worker_id=worker_id, role_name="Adversarial Critic Worker", model_router=model_router)

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        all_claims = blackboard.claim_registry.get_all()
        if not all_claims:
            return {
                "verified_claims": [],
                "rejected_claims": [],
                "deflated_claims": [],
                "contradictions": [],
                "confidence_calibration_score": None,
                "integrity_audit_summary": "No claims submitted for verification."
            }

        # 1. Flatten all agent claims into atoms: {claim_id, statement, severity, evidence_refs, source_agent}
        claim_atoms = []
        cited_ev_ids = set()
        for c in all_claims:
            claim_atoms.append({
                "claim_id": c.id,
                "statement": c.statement,
                "severity": c.severity.value,
                "evidence_refs": c.evidence_refs,
                "source_agent": c.agent_id
            })
            cited_ev_ids.update(c.evidence_refs)

        # 2. Build critic packet with cited ev slices + raw text of those IDs only
        focused_evidence = [
            ev for ev in blackboard.evidence_store.get_all()
            if ev.id in cited_ev_ids
        ]
        # If no evidence cited, provide empty slice
        if not focused_evidence:
            focused_evidence = blackboard.evidence_store.get_all()[:5]

        critic_prompt = load_prompt("critic")
        critic_card = (
            "You are an evidence clerk.\n"
            "Audit each claim against the attached evidence slices only.\n"
            "For each claim decide: supported | contradicted | unsupported | severity_inflated.\n"
            "supported: evidence directly backs the statement\n"
            "contradicted: evidence shows the opposite\n"
            "unsupported: not in the slices\n"
            "severity_inflated: directionally true but over-labeled (example: missing OG image is not CRITICAL)\n"
            "You may not raise severity. You may keep, lower, or reject.\n"
            "Prefer DOM facts when two claims conflict.\n"
            "Never invent missing DOM nodes. Quote ev IDs in rationale.\n"
            "Do not add strategy. Do not add numbers."
        )

        claims_json = json.dumps(claim_atoms, ensure_ascii=False, indent=2)
        task_contract = (
            f"{critic_prompt or critic_card}\n\n"
            f"<claims_to_audit>\n{claims_json}\n</claims_to_audit>"
        )

        raw_result = await self.model_router.generate_structured(
            capability="critic",
            agent_role="Lead Adversarial Falsification Arbiter & Evidence Clerk",
            task_contract=task_contract,
            evidence_list=focused_evidence,
            output_schema_desc=json.dumps(CriticOutput.model_json_schema(), indent=2),
            site_facts=getattr(blackboard, "site_facts", None),
            task_card=critic_card,
            max_claims=len(claim_atoms)
        )

        # Parse decisions
        results_list = raw_result.get("results", [])
        verified_ids = []
        rejected_claims = []
        deflated_claims = []
        contradictions = []

        decision_map = {}
        for r in results_list:
            if isinstance(r, dict):
                cid = r.get("claim_id")
                if cid:
                    decision_map[cid] = r

        for claim in all_claims:
            audit = decision_map.get(claim.id)
            if not audit:
                # If not explicitly audited by critic, remain PENDING_VERIFICATION (do not assume VERIFIED)
                claim.verification_status = VerificationStatus.PENDING_VERIFICATION
                claim.verification_notes = "Not evaluated in critic pass; remains pending verification."
                continue

            decision = audit.get("decision", "supported")
            rationale = audit.get("rationale", "")

            if decision == "supported":
                claim.verification_status = VerificationStatus.VERIFIED
                claim.verification_notes = rationale
                verified_ids.append(claim.id)
            elif decision in ["contradicted", "unsupported"]:
                claim.verification_status = VerificationStatus.REJECTED
                claim.verification_notes = f"[{decision.upper()}] {rationale}"
                rejected_claims.append({
                    "claim_id": claim.id,
                    "reason": rationale,
                    "decision": decision
                })
            elif decision == "severity_inflated":
                claim.verification_status = VerificationStatus.VERIFIED
                old_sev = claim.severity.value
                new_sev_str = str(audit.get("calibrated_severity") or "LOW").upper()
                for s in Severity:
                    if s.value == new_sev_str:
                        claim.severity = s
                        break
                claim.verification_notes = f"[DEFLATED from {old_sev} to {claim.severity.value}] {rationale}"
                verified_ids.append(claim.id)
                deflated_claims.append({
                    "claim_id": claim.id,
                    "original_severity": old_sev,
                    "calibrated_severity": claim.severity.value,
                    "reason": rationale
                })

            if audit.get("contradicting_ev"):
                for contra_ev in audit["contradicting_ev"]:
                    contra = blackboard.claim_registry.register_contradiction(
                        claim_a_id=claim.id,
                        claim_b_id=contra_ev,
                        description=rationale,
                        resolution="Arbitrated strictly against observed DOM evidence."
                    )
                    contradictions.append(contra.model_dump() if hasattr(contra, "model_dump") else str(contra))

        # 4. Code computes confidence_calibration_score = verified / evaluated
        total_eval = len(all_claims)
        verified_count = len(verified_ids)
        confidence_calibration_score = round(verified_count / max(1, total_eval), 2)

        output_summary = {
            "verified_claims": verified_ids,
            "rejected_claims": rejected_claims,
            "deflated_claims": deflated_claims,
            "contradictions": contradictions,
            "confidence_calibration_score": confidence_calibration_score,
            "integrity_audit_summary": f"Audited {total_eval} claims: {verified_count} verified, {len(rejected_claims)} rejected, {len(deflated_claims)} severity deflated."
        }

        blackboard.log_step("Adversarial Critic Falsification Completed (70B Blind)", self.worker_id, {
            "evaluated": total_eval,
            "verified": verified_count,
            "rejected": len(rejected_claims),
            "calibration_score": confidence_calibration_score
        })

        return output_summary
