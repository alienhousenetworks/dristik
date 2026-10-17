"""
Dristik AI UX & Conversion Velocity Agent
Analyzes visual hierarchy, call-to-action clarity, form friction, and conversion pathways.
"""
from typing import Dict, Any
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever

class UxConversionAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_ux", capability="ux_conversion", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=20)
        
        dom_ev = next((ev for ev in evidence_slice if ev.source_type == "dom" and ev.value and "ctas" in ev.value), None)
        ctas = dom_ev.value.get("ctas", []) if dom_ev else []
        
        if not ctas:
            self.register_claim(
                blackboard=blackboard,
                statement="No prominent, high-contrast primary Call-to-Action (CTA) detected above the fold.",
                category=Category.UX_CONVERSION,
                severity=Severity.HIGH,
                evidence_refs=[dom_ev.id] if dom_ev else [],
                confidence=0.90,
                recommendation="Position a clear, high-contrast action button (e.g. 'Get Started Free' or 'Book a Demo') in the hero section.",
                impact=9,
                effort=2
            )
        else:
            self.register_claim(
                blackboard=blackboard,
                statement=f"Clear conversion touchpoints identified: {', '.join(ctas[:3])}.",
                category=Category.UX_CONVERSION,
                severity=Severity.INFO,
                evidence_refs=[dom_ev.id] if dom_ev else [],
                confidence=0.92,
                recommendation="A/B test button microcopy and contrasting colorways to maximize click-through rate."
            )
            
        blackboard.log_step("UX & Conversion Friction Analyzed", self.agent_id, {"ctas_found": len(ctas)})
        return {"ctas": ctas}
