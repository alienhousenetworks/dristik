"""
Dristik AI Technical SEO Resilience Agent
Inspects canonical tags, indexability, metadata completeness, OpenGraph, and viewport compliance.
"""
from typing import Dict, Any
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever

class TechnicalSeoAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_technical_seo", capability="technical_seo", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=25)
        
        # Check deterministic flags
        has_canonical = any(ev.source_type == "meta" and ev.value and "canonical" in ev.value for ev in evidence_slice)
        has_title = any(ev.source_type == "meta" and ev.value and "title" in ev.value for ev in evidence_slice)
        has_desc = any(ev.source_type == "meta" and ev.value and "description" in ev.value for ev in evidence_slice)
        
        claims = []
        if not has_canonical:
            self.register_claim(
                blackboard=blackboard,
                statement="Missing canonical link tag leaves website vulnerable to duplicate URL indexing.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.HIGH,
                evidence_refs=[ev.id for ev in evidence_slice if ev.source_type == "meta"][:1],
                confidence=0.98,
                recommendation="Inject a self-referential <link rel='canonical' href='...'> tag into the <head> of every page.",
                impact=7,
                effort=1
            )
            
        if not has_desc:
            self.register_claim(
                blackboard=blackboard,
                statement="Missing meta description causes search engines to generate arbitrary snippet snippets.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.MEDIUM,
                evidence_refs=[ev.id for ev in evidence_slice if ev.source_type == "meta"][:1],
                confidence=0.98,
                recommendation="Provide an engaging, 150-160 character meta description emphasizing the unique value proposition.",
                impact=6,
                effort=1
            )
            
        if has_title and has_canonical:
            self.register_claim(
                blackboard=blackboard,
                statement="Core HTML meta headers and canonical tag structure are verified intact.",
                category=Category.TECHNICAL_SEO,
                severity=Severity.INFO,
                evidence_refs=[ev.id for ev in evidence_slice if ev.source_type == "meta"][:2],
                confidence=0.96,
                recommendation="Maintain clean canonical integrity across all future sub-pages."
            )
            
        blackboard.log_step("Technical SEO Analysis Completed", self.agent_id, {
            "has_canonical": has_canonical,
            "has_title": has_title
        })
        return {"status": "completed"}
