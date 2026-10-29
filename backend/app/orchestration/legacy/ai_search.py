"""
Dristik AI Answerability Simulation Agent (70B-Hardened)
Simulates synthetic buyer queries across ChatGPT Search, Perplexity, and AI Overviews.
Archetypal queries are generated strictly in code, not authored by the model.
"""
import json
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple
from app.agents.runtime.base import BaseAgent
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import AiSearchQueryEvaluation
from app.domain.enums import Category, Severity
from app.evidence.retriever import EvidenceRetriever
from app.inference.prompt_compiler import load_prompt
from app.inference.schemas import AiSearchBatchOutput, legacy_adapt

def commercial_queries(name: str) -> List[Tuple[str, str]]:
    """Generates the 6 canonical commercial query archetypes deterministically in code."""
    return [
        ("identity", f"What does {name} do and what is its core value proposition?"),
        ("icp", f"Who is {name} built for, and which buyer roles qualify?"),
        ("pricing", f"How is {name} priced, packaged, and what is total cost of ownership?"),
        ("competition", f"How does {name} compare to alternatives, and what is its moat?"),
        ("trust", f"What security, compliance, and customer proof does {name} publish?"),
        ("roi", f"What business case or cost of inaction does {name} state?"),
    ]

class AiSearchSimulationAgent(BaseAgent):
    def __init__(self, model_router):
        super().__init__(agent_id="agent_ai_search", capability="ai_search_simulation", model_router=model_router)

    async def run(self, blackboard: CognitiveBlackboard) -> Dict[str, Any]:
        retriever = EvidenceRetriever(blackboard.evidence_store)
        evidence_slice = retriever.retrieve_for_agent(self.capability, limit=25)
        site_facts = getattr(blackboard, "site_facts", {}) or {}

        # Determine firm name or fallback to domain
        name = "the company"
        if blackboard.business_profile and blackboard.business_profile.business_name and blackboard.business_profile.business_name not in ["Unknown", "Unknown Business", "Identified Platform"]:
            name = blackboard.business_profile.business_name
        elif site_facts.get("business_name_candidates"):
            name = site_facts["business_name_candidates"][0]
        elif blackboard.website_url:
            name = urlparse(blackboard.website_url).netloc.replace("www.", "").split(".")[0].capitalize()

        queries = commercial_queries(name)
        queries_formatted = "\n".join([f"- [{q_type}] \"{q_text}\"" for q_type, q_text in queries])

        ai_prompt = load_prompt("ai_search")
        ai_card = (
            "For each query, answer only from evidence.\n"
            "If the page does not contain a citable answer, detected_answer=\"cannot answer from site\" and evidence_quality=\"none\" or \"weak\".\n"
            "citation_readiness:\n"
            "  high = a 40–60 word block plus schema or table\n"
            "  medium = scattered facts a model could stitch\n"
            "  low = missing or only marketing adjectives\n"
            "hallucination_vulnerability is high when buyers will ask a question the page refuses to answer (especially pricing, compliance, ROI)."
        )

        full_contract = (
            f"Simulate AI answer engine evaluation for these exact 6 commercial queries:\n"
            f"{queries_formatted}\n\n"
            f"{ai_prompt or ai_card}\n"
            "Evaluate all 6 independent slots without inventing missing data. Formulate at most 2 claims."
        )

        result = await self.model_router.generate_structured(
            capability=self.capability,
            agent_role="Principal AI Answer Engine Research Director (ChatGPT Search, Perplexity, Gemini, Claude)",
            task_contract=full_contract,
            evidence_list=evidence_slice,
            output_schema_desc=json.dumps(AiSearchBatchOutput.model_json_schema(), indent=2),
            site_facts=site_facts,
            task_card=ai_card,
            max_claims=2
        )

        adapted = legacy_adapt("ai_search", result)

        evals: List[AiSearchQueryEvaluation] = []
        raw_evals = adapted.get("evaluations", [])

        # Ensure we cover all 6 queries even if the LLM dropped one
        for q_type, q_text in queries:
            matched_eval = None
            for ev in raw_evals:
                if isinstance(ev, dict) and (q_type.lower() in ev.get("question_type", "").lower() or q_text[:20].lower() in ev.get("query", "").lower()):
                    matched_eval = ev
                    break

            if matched_eval:
                detected_ans = matched_eval.get("detected_answer", "cannot answer from site")
                eq = matched_eval.get("evidence_quality", "none")
                score = matched_eval.get("score")
                gap = matched_eval.get("gap_analysis", "No direct on-page data found.")
                cit_prob = matched_eval.get("citation_probability")
                halluc = matched_eval.get("hallucination_vulnerability_risk", "High")
                remed = matched_eval.get("recommended_remediation", "Add declarative factual answer block.")
            else:
                detected_ans = "cannot answer from site"
                eq = "none"
                score = None
                gap = f"No direct on-page information answering '{q_text}'."
                cit_prob = None
                halluc = "High"
                remed = "Add clear declarative section answering this query."

            evals.append(AiSearchQueryEvaluation(
                query=q_text,
                question_type=q_type.capitalize(),
                evidence_quality=eq.capitalize() if isinstance(eq, str) else "Weak",
                score=int(score) if score is not None else None,
                detected_answer=detected_ans,
                gap_analysis=gap,
                citation_probability=float(cit_prob) if cit_prob is not None else None,
                hallucination_vulnerability_risk=halluc,
                recommended_remediation=remed
            ))

        blackboard.ai_search_evaluations = evals
        if adapted.get("aggregate_citation_probability"):
            blackboard.blackboard_state["aggregate_citation_probability"] = adapted["aggregate_citation_probability"]

        # Register claims (max 2)
        for c in adapted.get("claims", [])[:2]:
            sev_str = str(c.get("severity", "MEDIUM")).upper()
            sev_enum = Severity.MEDIUM
            for s in Severity:
                if s.value == sev_str:
                    sev_enum = s
                    break

            conf_val = c.get("confidence")
            confidence = float(conf_val) if conf_val is not None else (0.80 if c.get("evidence_refs") else 0.50)

            self.register_claim(
                blackboard=blackboard,
                statement=c.get("statement", "AI search answerability evaluated."),
                category=Category.AI_SEARCH,
                severity=sev_enum,
                evidence_refs=c.get("evidence_refs") or [],
                confidence=confidence,
                recommendation=c.get("recommendation", "Implement structured FAQ blocks for AI citation capture."),
                impact=c.get("impact", 8),
                effort=c.get("effort", 3)
            )

        blackboard.log_step("AI Search Simulation Completed (70B Hardened)", self.agent_id, {
            "simulated_queries": len(evals),
            "aggregate_citation_prob": adapted.get("aggregate_citation_probability", 0.40)
        })
        return {"evaluations_count": len(evals)}
