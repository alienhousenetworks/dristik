"""
Dristik AI Strategist Worker (70B-Hardened Theory of Constraints)
Isolates single root bottleneck using Theory of Constraints from verified claims only.
Calculates composite ICE scores deterministically in code.
"""
import json
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity, VerificationStatus
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import StrategistOutput, legacy_adapt

class CognitiveStrategistWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(
            worker_id=worker_id,
            role_name="Principal Strategic Architect & Growth Consultant",
            model_router=model_router
        )

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        all_claims = blackboard.claim_registry.get_all()
        # Strictly isolate verified claims
        verified_claims = [c for c in all_claims if c.verification_status == VerificationStatus.VERIFIED]
        bp = blackboard.business_profile
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        biz_name = bp.business_name if bp and bp.business_name not in ["Unknown", "Unknown Business", "Identified Platform"] else "the target enterprise"
        niche_str = bp.niche if bp else "Digital Solutions"

        claims_summary = "\n".join([
            f"[{c.id}] ({c.category.value} | {c.severity.value}): {c.statement}"
            for c in verified_claims[:15]
        ])

        strat_prompt = load_prompt("strategist")
        strat_card = (
            "Name one root bottleneck using Theory of Constraints.\n"
            "causes_chain must be 3–5 bullets, each either citing a verified claim id or a Wave-0 fact.\n"
            "Propose up to 3 growth levers with impact, confidence, ease (1-10) and a one-line basis each.\n"
            "Ignore vanity work that does not remove the bottleneck.\n"
            "Max 3 strategic_claims, each pointing at a verified claim id when possible."
        )

        task_contract = (
            f"{strat_prompt or strat_card}\n\n"
            f"Target Enterprise: {biz_name} ({niche_str})\n"
            f"Verified Claims Input:\n{claims_summary or 'Baseline site observations only.'}"
        )

        focused_evidence = [
            ev for ev in blackboard.evidence_store.get_all()
            if any(ev.id in c.evidence_refs for c in verified_claims)
        ][:15]

        result = await self.model_router.generate_structured(
            capability="synthesizer",
            agent_role="Principal Strategic Growth Architect (Theory of Constraints)",
            task_contract=task_contract,
            evidence_list=focused_evidence,
            output_schema_desc=json.dumps(StrategistOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card=strat_card,
            max_claims=3
        )

        adapted = legacy_adapt("strategist", result)

        # Ensure composite ICE score is strictly calculated in code
        for opp in adapted.get("growth_opportunities", []):
            if isinstance(opp, dict) and "ice_score" in opp and isinstance(opp["ice_score"], dict):
                ice = opp["ice_score"]
                i = int(ice.get("impact", 5))
                c = int(ice.get("confidence", 5))
                e = int(ice.get("ease", 5))
                ice["impact"] = max(1, min(10, i))
                ice["confidence"] = max(1, min(10, c))
                ice["ease"] = max(1, min(10, e))
                ice["composite"] = round((ice["impact"] + ice["confidence"] + ice["ease"]) / 3.0, 1)

        # Store in blackboard state
        blackboard.blackboard_state["causal_root_cause"] = adapted.get("primary_root_cause", {})
        blackboard.blackboard_state["growth_opportunities"] = adapted.get("growth_opportunities", [])
        blackboard.blackboard_state["what_to_ignore"] = adapted.get("what_to_ignore", "")

        # Register Strategic Claims (max 3)
        for cl in adapted.get("strategic_claims", [])[:3]:
            cat_str = str(cl.get("category", "COMPETITIVE")).upper()
            cat = Category[cat_str] if cat_str in Category.__members__ else Category.COMPETITIVE
            sev_str = str(cl.get("severity", "HIGH")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.HIGH

            self.register_claim(
                blackboard=blackboard,
                statement=cl.get("statement", "Strategic bottleneck diagnostic"),
                category=cat,
                severity=sev,
                evidence_refs=cl.get("evidence_refs", []),
                confidence=float(cl.get("confidence", 0.90)),
                recommendation=cl.get("recommendation"),
                impact=int(cl.get("impact", 8)),
                effort=int(cl.get("effort", 3))
            )

        blackboard.log_step("Strategic Bottleneck Discovery Completed (70B Hardened)", self.worker_id, {
            "root_bottleneck": adapted.get("primary_root_cause", {}).get("bottleneck", "Unspecified"),
            "growth_levers": len(adapted.get("growth_opportunities", []))
        })

        return adapted
