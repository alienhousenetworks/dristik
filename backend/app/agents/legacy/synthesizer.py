"""
Dristik AI Executive Synthesizer Agent
Fuses verified claims into strategic intelligence, 3-Way Perspectives, and C-Suite consulting story.
"""
from typing import Dict, Any
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.evidence.retriever import EvidenceRetriever

class ExecutiveSynthesizerAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_synthesizer", capability="synthesizer", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=30)
        
        claims = [c.statement for c in blackboard.claim_registry.get_all() if c.verification_status.value == "verified"]
        claims_summary = "\n- " + "\n- ".join(claims[:8]) if claims else "No critical claims recorded."
        
        role = "Principal auditor writing a board diagnostic from verified claims only"
        contract = (
            "Synthesize verified technical, positioning, and GEO findings into a C-suite diagnostic. "
            "Name the business, the offer, the buyer, and the single deepest constraint. No generic SEO essay.\n"
            "1. STORY SUMMARY: 5-8 sentences. Constraint first. Then what a first-time buyer, Googlebot, and an answer engine each fail to extract.\n"
            "2. WHAT SITE GETS RIGHT: 3 items, each a named page/element and why it helps.\n"
            "3. WHAT IS HOLDING IT BACK: 3 root causes, not a symptom dump.\n"
            "4. PRIMARY STRATEGIC OPPORTUNITY: One lever, named asset, why it unblocks pipeline.\n"
            "5. CONSULTANT ADVICE (WHAT TO IGNORE): Name vanity work that does not remove the constraint.\n"
            "6. THREE-WAY PERSPECTIVE COMPARISON: three DISTINCT failure modes (human / search_engine / ai_answer_engine), not paraphrases.\n"
            "7. PRIORITIZED ROADMAP: 7-day, 30-day, 90-day. Each item names a page or file.\n"
            "Forbidden: invented competitors, TAM, traffic, citation %, currency, or 'McKinsey-grade' filler."
        )
        rubric = (
            "1. Lead with the commercial constraint. Every sentence traces to a verified claim or site_fact.\n"
            "2. Three-way perspectives must disagree with each other (buyer vs crawler vs LLM).\n"
            "3. Roadmaps are engineering-ready. No 'improve content'.\n"
            "4. If verified claims are thin, say so. Do not pad."
        )
        schema_desc = """{
  "story_summary": "string",
  "what_site_gets_right": ["string"],
  "what_is_holding_it_back": ["string"],
  "primary_strategic_opportunity": "string",
  "consultant_advice_what_to_ignore": "string",
  "three_way_comparison": {
    "human_visitor_perspective": "string",
    "search_engine_perspective": "string",
    "ai_answer_engine_perspective": "string"
  },
  "roadmap_7_days": [
    {"title": "string", "description": "string", "impact": "High | Medium", "effort": "Low"}
  ],
  "roadmap_30_days": [
    {"title": "string", "description": "string", "impact": "High | Medium", "effort": "Medium"}
  ],
  "roadmap_90_days": [
    {"title": "string", "description": "string", "impact": "High", "effort": "High"}
  ]
}"""

        context = f"""BUSINESS PROFILE:
Name: {blackboard.business_profile.business_name if blackboard.business_profile else 'Platform'}
Model: {blackboard.business_profile.business_model if blackboard.business_profile else 'B2B'}
Value Prop: {blackboard.business_profile.value_proposition if blackboard.business_profile else 'Services'}

VERIFIED AGENT FINDINGS:{claims_summary}
"""

        result = await self.model_router.generate_structured(
            capability=self.capability,
            agent_role=role,
            task_contract=contract,
            evidence_list=evidence_slice,
            rubric=rubric,
            output_schema_desc=schema_desc,
            additional_context=context
        )
        
        blackboard.executive_narrative = result
        blackboard.log_step("Executive Strategic Synthesis Completed", self.agent_id, {
            "strategic_opportunity": result.get("primary_strategic_opportunity", "Scale entity schema.")
        })
        return result
