"""
Dristik AI Executive Synthesizer Worker (70B-Hardened Minto Synthesis)
Synthesizes verified claims and Wave-0 site facts into an authoritative C-Suite brief.
Strictly isolates verified claims from rejected claims, raw agent dumps, and invented metrics.
"""
import json
from typing import Dict, Any, Optional
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import VerificationStatus
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import SynthesizerOutput, legacy_adapt

class CognitiveSynthesizerWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(worker_id=worker_id, role_name="Senior Managing Director - C-Suite Strategy & Growth Intelligence", model_router=model_router)

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # 1. Filter strictly VERIFIED claims only (exclude REJECTED or uncorroborated)
        all_claims = blackboard.claim_registry.get_all()
        verified_claims = [c for c in all_claims if c.verification_status == VerificationStatus.VERIFIED]

        site_facts = getattr(blackboard, "site_facts", {}) or {}
        bp = blackboard.business_profile
        biz_name = bp.business_name if bp and bp.business_name not in ["Unknown", "Unknown Business", "Identified Platform"] else "the target enterprise"

        # Construct verified claims packet
        verified_claims_summary = [
            {
                "claim_id": c.id,
                "category": c.category.value,
                "severity": c.severity.value,
                "statement": c.statement,
                "evidence_refs": c.evidence_refs,
                "recommendation": c.recommendation
            }
            for c in verified_claims[:15]
        ]

        # AI search bands
        ai_eval_bands = [
            {
                "query": e.query,
                "evidence_quality": e.evidence_quality,
                "detected_answer": e.detected_answer,
                "gap": e.gap_analysis
            }
            for e in (blackboard.ai_search_evaluations or [])[:6]
        ]

        # GEO inventory
        geo_inventory = {
            "schemas_detected": site_facts.get("schemas_detected", []),
            "sameas_urls": site_facts.get("sameas_urls", []),
            "faq_questions": site_facts.get("faq_questions", [])
        }

        identity_context = {
            "business_name": biz_name,
            "industry": bp.industry if bp else "Software & Services",
            "value_proposition": bp.value_proposition if bp else "",
            "primary_intent": bp.primary_intent.value if bp and hasattr(bp.primary_intent, "value") else "lead_generation"
        }

        verified_packet = {
            "identity": identity_context,
            "geo_inventory": geo_inventory,
            "ai_search_evaluations": ai_eval_bands,
            "verified_claims": verified_claims_summary
        }

        synth_prompt = load_prompt("synthesizer")
        synth_card = (
            "Produce the C-suite diagnostic from verified claims and site_facts only.\n"
            "Write a Minto CEO brief from verified claims only.\n"
            "Lead with the single deepest commercial constraint.\n"
            "what_site_gets_right: 3 items, each grounded.\n"
            "what_is_holding_it_back: 3 items.\n"
            "financial_impact_model: uses bands only (cac_pressure, organic_pipeline_at_risk, conversion_velocity_uplift).\n"
            "Do not introduce new statistics.\n"
            "what_to_ignore must name tactics that do not fix the stated root constraint.\n"
            "Max 3 board bullets."
        )

        packet_json = json.dumps(verified_packet, ensure_ascii=False, indent=2)
        task_contract = (
            f"{synth_prompt or synth_card}\n\n"
            f"<verified_audit_packet>\n{packet_json}\n</verified_audit_packet>"
        )

        focused_evidence = [
            ev for ev in blackboard.evidence_store.get_all()
            if any(ev.id in c.evidence_refs for c in verified_claims)
        ][:15]

        result = await self.model_router.generate_structured(
            capability="synthesizer",
            agent_role="Senior Managing Partner & Board Advisor - Enterprise Strategy (Minto Diagnostic)",
            task_contract=task_contract,
            evidence_list=focused_evidence,
            output_schema_desc=json.dumps(SynthesizerOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card=synth_card,
            max_claims=0
        )

        adapted = legacy_adapt("synthesizer", result)
        blackboard.executive_narrative = adapted
        return adapted
