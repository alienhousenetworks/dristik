"""
Dristik AI Content Depth & Readability Agent
Analyzes reading ease, heading structure, topical depth, and thin content risks.
"""
from typing import Dict, Any
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever

class ContentAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_content", capability="content_intelligence", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=20)
        
        # Check word count and readability from evidence
        content_ev = next((ev for ev in evidence_slice if ev.source_type == "content" and isinstance(ev.value, dict)), None)
        word_count = content_ev.value.get("word_count") if content_ev else None
        readability = content_ev.value.get("readability_score") if content_ev else None
        
        if word_count is not None and word_count < 200:
            self.register_claim(
                blackboard=blackboard,
                statement=f"Landing page copy is thin ({word_count} words), potentially restricting topical authority.",
                category=Category.CONTENT,
                severity=Severity.HIGH,
                evidence_refs=[content_ev.id] if content_ev else [],
                confidence=0.85,
                recommendation="Expand core landing page with detailed feature breakdowns, customer problem-solution context, and FAQs.",
                impact=7,
                effort=4
            )
        elif word_count is not None:
            self.register_claim(
                blackboard=blackboard,
                statement=f"Textual content volume ({word_count} words)" + (f" with a readability score of {readability}/100." if readability is not None else "."),
                category=Category.CONTENT,
                severity=Severity.INFO,
                evidence_refs=[content_ev.id] if content_ev else [],
                confidence=0.85,
                recommendation="Continue organizing content into scannable subheadings and bullet points."
            )
        else:
            self.register_claim(
                blackboard=blackboard,
                statement="Content text volume and readability metrics unmeasured from initial crawl extraction.",
                category=Category.CONTENT,
                severity=Severity.INFO,
                evidence_refs=[],
                confidence=0.40,
                recommendation="Ensure main content areas are renderable HTML and not obfuscated behind client-only scripts."
            )
            
        blackboard.log_step("Content Intelligence Analyzed", self.agent_id, {
            "word_count": word_count,
            "readability": readability
        })
        return {"word_count": word_count, "readability": readability}
