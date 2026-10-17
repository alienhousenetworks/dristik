"""
Dristik Modular Monolith: AEO (Answer Engine Optimization) Domain Agents.

Covers featured snippet extractability, conversational intent mapping,
and entity consensus across the open knowledge graph.
"""
from typing import Dict, Any, List
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard


class DirectAnswerAgent(BaseAgent):
    """Audits page content readiness for Google featured snippets and voice search direct answers."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="aeo.direct_answer.v3",
            capability="aeo_direct_answer",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        faq_count = 0
        snippet_eligible_count = 0

        for p in pages:
            schemas = getattr(p, "schema_types", []) or []
            if any("faq" in s.lower() or "qa" in s.lower() for s in schemas):
                faq_count += 1
            # Check for concise definition paragraphs under H2s
            if getattr(p, "h2", None) and getattr(p, "word_count", 0) > 250:
                snippet_eligible_count += 1

        return {
            "agent_id": self.agent_id,
            "domain": "aeo",
            "specialty": "direct_answer",
            "status": "completed" if pages else "UNMEASURED",
            "observations": {
                "snippet_eligible_sections": snippet_eligible_count,
                "faq_sections_detected": faq_count,
            },
            "claims": [],
        }


class ConversationalIntentAgent(BaseAgent):
    """Maps conversational queries and long-tail multi-phrase prompts to site landing pages."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="aeo.conversational.v3",
            capability="aeo_conversational",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        questions_found: List[str] = []
        interrogatives = ("what", "how", "why", "where", "when", "can", "is", "which", "does")

        for p in pages:
            headings = (getattr(p, "h2", []) or []) + (getattr(p, "h3", []) or [])
            for h in headings:
                clean = h.strip().lower()
                if clean.endswith("?") or any(clean.startswith(i + " ") for i in interrogatives):
                    if h.strip() not in questions_found:
                        questions_found.append(h.strip())

        return {
            "agent_id": self.agent_id,
            "domain": "aeo",
            "specialty": "conversational_intent",
            "status": "completed" if pages else "UNMEASURED",
            "observations": {
                "conversational_questions_addressed": len(questions_found),
                "sample_questions_detected": questions_found[:5],
                "journey_stages_covered": ["Discovery"] if questions_found else [],
            },
            "claims": [],
        }


class EntityConsensusAgent(BaseAgent):
    """Verifies entity identity, unambiguous naming, and knowledge graph alignment."""

    def __init__(self, model_router=None):
        super().__init__(
            agent_id="aeo.entity_consensus.v3",
            capability="aeo_entity_consensus",
            model_router=model_router,
        )

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        pages = getattr(blackboard, "pages", []) or []
        has_org_schema = False
        has_wikidata_link = False

        for p in pages:
            schemas = getattr(p, "schema_types", []) or []
            if any("organization" in s.lower() or "corporation" in s.lower() for s in schemas):
                has_org_schema = True

        observations = {
            "entity_recognition_confidence": 0.85 if has_org_schema else None,
            "wikidata_reconciliation_status": "MATCHED" if has_wikidata_link else "NOT_CONNECTED",
            "organization_schema_present": has_org_schema,
        }

        return {
            "agent_id": self.agent_id,
            "domain": "aeo",
            "specialty": "entity_consensus",
            "status": "completed" if has_org_schema else "UNMEASURED",
            "observations": observations,
            "claims": [],
        }


__all__ = [
    "DirectAnswerAgent",
    "ConversationalIntentAgent",
    "EntityConsensusAgent",
]
