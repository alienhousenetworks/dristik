"""
Dristik AI Business Intelligence & Positioning Agent (70B-Hardened Split Architecture)
Splits commercial analysis into:
- Task A: Deterministic/Zero-Temp Commercial Extraction (`business_extract`)
- Task B: Reason-Then-JSON Commercial Positioning Diagnosis (`business_position`)
"""
import json
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import BusinessProfile
from app.domain.enums import BusinessIntent, Category, Severity
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import (
    BusinessExtractOutput,
    BusinessPositionOutput,
    legacy_adapt,
)

class BusinessIntelligenceAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_business", capability="business_intelligence", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        # Evidence allowlist: homepage title/meta, logo/alt, footer copyright, H1, hero, primary nav, pricing teaser, CTA buttons
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=25)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        # ----------------------------------------------------------------------
        # Task A: Business Extract (Commercial Identity, temp 0.0)
        # ----------------------------------------------------------------------
        extract_prompt = load_prompt("business_extract")
        extract_card = (
            "Extract commercial identity. Do not strategize. Do not rewrite copy.\n"
            "Use only <site_facts> and <evidence>.\n"
            "If a field is not written on the page, return null."
        )

        extract_res = await self.model_router.generate_structured(
            capability="business_extract",
            agent_role="Commercial Identity Extraction Specialist",
            task_contract=extract_prompt or extract_card,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(BusinessExtractOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card=extract_card,
            max_claims=0
        )

        # ----------------------------------------------------------------------
        # Task B: Business Position (Two-Pass Reason-Then-JSON Diagnosis)
        # ----------------------------------------------------------------------
        position_prompt = load_prompt("business_position")
        position_card = (
            "Judge ICP sharpness, 5-second clarity, moat type, and conversion friction.\n"
            "Write at most 3 claims. Each claim needs evidence_refs.\n"
            "Produce BEFORE->AFTER only for strings that exist in evidence.\n"
            "Do not invent metrics. Use qualitative bands."
        )

        extract_context = json.dumps(extract_res, ensure_ascii=False)
        position_res = await self.model_router.run_reason_then_json(
            capability="business_position",
            agent_role="Principal Commercial Strategy & Enterprise Positioning Auditor",
            reason_contract=f"EXTRACT:\n{extract_context}\n\n{position_prompt or position_card}",
            schema_cls=BusinessPositionOutput,
            evidence_list=evidence_slice,
            site_facts=site_facts,
            task_card=position_card
        )

        # ----------------------------------------------------------------------
        # Merge A + B in Code into Canonical Profile
        # ----------------------------------------------------------------------
        merged = {**extract_res, **position_res}
        adapted = legacy_adapt("business", merged)

        intent_str = adapted.get("primary_intent", "lead_generation").lower()
        intent_enum = BusinessIntent.LEAD_GENERATION
        for bi in BusinessIntent:
            if bi.value == intent_str:
                intent_enum = bi
                break

        # Fallback to candidates from site_facts if business_name is missing
        biz_name = adapted.get("business_name")
        if not biz_name and site_facts.get("business_name_candidates"):
            biz_name = site_facts["business_name_candidates"][0]

        profile = BusinessProfile(
            business_name=biz_name or "Unknown Business",
            industry=adapted.get("industry"),
            niche=adapted.get("niche"),
            target_audience=adapted.get("target_audience"),
            business_model=adapted.get("business_model"),
            value_proposition=adapted.get("value_proposition"),
            primary_cta=adapted.get("primary_cta"),
            secondary_cta=adapted.get("secondary_cta"),
            primary_intent=intent_enum,
            confidence=float(adapted.get("confidence", 0.50)) if adapted.get("confidence") is not None else None,
            economic_buyer_title=adapted.get("economic_buyer_title"),
            target_org_scale=adapted.get("target_org_scale"),
            defensible_moat_type=adapted.get("defensible_moat_type"),
            five_second_clarity_score=adapted.get("five_second_clarity_score"),
            cac_impact_risk=adapted.get("cac_impact_risk"),
            copy_rewrite=adapted.get("copy_rewrite")
        )
        blackboard.business_profile = profile

        # Store diagnostics in blackboard
        if adapted.get("copy_rewrite"):
            blackboard.blackboard_state["hero_copy_rewrite"] = adapted.get("copy_rewrite")
        if adapted.get("five_second_clarity_score"):
            blackboard.blackboard_state["five_second_clarity_score"] = adapted.get("five_second_clarity_score")

        # Register claims (capped at 3)
        claims_list = adapted.get("claims", [])[:3]
        for c in claims_list:
            sev_str = str(c.get("severity", "MEDIUM")).upper()
            sev_enum = Severity.MEDIUM
            for s in Severity:
                if s.value == sev_str:
                    sev_enum = s
                    break

            self.register_claim(
                blackboard=blackboard,
                statement=c.get("statement", "Commercial positioning analyzed."),
                category=Category.UX_CONVERSION,
                severity=sev_enum,
                evidence_refs=c.get("evidence_refs") or [],
                confidence=profile.confidence if profile.confidence is not None else (float(c.get("confidence")) if c.get("confidence") is not None else 0.50),
                recommendation=c.get("recommendation", "Refine positioning copy."),
                impact=c.get("impact", 7),
                effort=c.get("effort", 2)
            )

        blackboard.log_step("Business Positioning Analyzed (70B Split)", self.agent_id, {
            "business_name": profile.business_name,
            "intent": profile.primary_intent.value,
            "clarity_band": position_res.get("five_second_clarity", {}).get("band", "unknown"),
            "five_second_clarity": profile.five_second_clarity_score
        })
        return {"profile": profile.model_dump(), "raw": adapted}
