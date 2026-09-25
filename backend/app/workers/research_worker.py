"""
Dristik AI Cognitive Research Worker - Enterprise AI Search Simulation
Simulates autonomous AI engine discovery queries (ChatGPT Search, Perplexity, Gemini Overviews, Claude)
across 5 core enterprise commercial dimensions.
"""
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import AiSearchQueryEvaluation
from app.domain.enums import Category, Severity

class CognitiveResearchWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(worker_id=worker_id, role_name="Principal AI Retrieval & Search Simulation Researcher", model_router=model_router)

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        evidence_list = blackboard.evidence_store.get_all()
        bp = blackboard.business_profile
        biz_name = bp.business_name if bp and bp.business_name not in ["Unknown", "Unknown Business"] else "the target company"
        domain = blackboard.website_url.replace("https://", "").replace("http://", "").rstrip("/")
        
        prompt_contract = (
            f"SIMULATION_ONLY. Using on-page evidence, judge whether an answer engine could reply when buyers research '{biz_name}' ({domain}). "
            f"Do not fabricate live ChatGPT/Perplexity/Gemini output, search volume, or competitors.\n\n"
            "Evaluate EXACTLY 5 commercial queries:\n"
            f"1. Query: 'What does {biz_name} do and what is its core value proposition?' (Category: Identity & Offering)\n"
            f"2. Query: 'Who is {biz_name} built for and what are primary customer use cases?' (Category: Target Audience / ICP)\n"
            f"3. Query: 'How much does {biz_name} cost and what are the pricing/contract models?' (Category: Pricing & Commercial Transparency)\n"
            f"4. Query: 'What is the technical architecture, security compliance, and integration ecosystem of {biz_name}?' (Category: Technical & Compliance)\n"
            f"5. Query: 'How does {biz_name} compare against leading market alternatives and what is its moat?' (Category: Competitive Differentiation)\n\n"
            "For each query, output:\n"
            "- query (exact string)\n"
            "- question_type (category label)\n"
            "- evidence_quality ('Excellent', 'Good', 'Moderate', 'Weak', 'Missing')\n"
            "- score (1-10 numerical citability score)\n"
            "- detected_answer (1-2 sentences of what the AI model directly synthesizes from crawled page text)\n"
            "- gap_analysis (concrete diagnostic explaining missing facts, schema deficiencies, or ambiguous messaging)\n"
            "- citation_probability (0.0 to 1.0 probability of getting cited as a primary source footnote)\n\n"
            "Also output 2 high-priority AI Search audit claims."
        )
        
        schema_desc = (
            "{\n"
            '  "ai_search_matrix": [\n'
            '    {\n'
            '      "query": "What does company do...",\n'
            '      "question_type": "Identity & Offering",\n'
            '      "evidence_quality": "Good",\n'
            '      "score": 8,\n'
            '      "detected_answer": "Company provides...",\n'
            '      "gap_analysis": "Answer is discernible from top headers...",\n'
            '      "citation_probability": 0.85\n'
            '    }\n'
            '  ],\n'
            '  "claims": [\n'
            '    {\n'
            '      "statement": "AI search discoverability finding",\n'
            '      "category": "AI_SEARCH",\n'
            '      "severity": "HIGH | MEDIUM | LOW",\n'
            '      "confidence": 0.92,\n'
            '      "impact": 8,\n'
            '      "effort": 3,\n'
            '      "evidence_refs": ["ev_id1"],\n'
            '      "recommendation": "Deploy structured FAQ schema and concise answer summary blocks."\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        result = await self.model_router.generate_structured(
            capability="ai_search_simulation",
            agent_role="Director of Generative Search Benchmarking & LLM Answerability",
            task_contract=prompt_contract,
            evidence_list=evidence_list,
            rubric=(
                "1. RAG RETRIEVAL FIDELITY: Synthesize detected answers strictly from on-page evidence. If a query dimension (e.g. pricing or compliance) is absent, mark evidence_quality as 'Missing', assign score <= 4, and record that AI engines will experience retrieval failure or hallucinate.\n"
                "2. CITATION SCORING CALIBRATION: Score 8-10 requires a 40-60 word self-contained paragraph under a descriptive header. Score 5-7 for fragmented data. Score 1-4 for missing data or slogans. Never score 8+ when that query's facts are absent.\n"
                "3. STRUCTURAL GAP DIAGNOSIS: Provide precise architectural diagnoses (e.g. missing Schema.org FAQPage, absent pricing table, buried use-case text).\n"
                "4. EVIDENCE GROUNDING: Audit claims must reference specific evidence IDs [ev_xxx]."
            ),
            output_schema_desc=schema_desc,
            additional_context=f"Business Profile Context: {bp.model_dump_json() if bp else ''}"
        )

        # Support all key aliases
        matrix_items = result.get("ai_search_matrix") or result.get("evaluations") or result.get("matrix") or result.get("queries") or []
        parsed_evals: List[AiSearchQueryEvaluation] = []
        
        for item in matrix_items:
            try:
                s = int(item["score"]) if item.get("score") is not None else None
                cp = float(item["citation_probability"]) if item.get("citation_probability") is not None else None
                parsed_evals.append(AiSearchQueryEvaluation(
                    query=item.get("query", f"What is {biz_name}?"),
                    question_type=item.get("question_type", "General Query"),
                    evidence_quality=item.get("evidence_quality", "Moderate"),
                    score=s,
                    detected_answer=item.get("detected_answer", "Synthesized from crawled domain headers and metadata."),
                    evidence_snippet=item.get("evidence_snippet"),
                    gap_analysis=item.get("gap_analysis", "Embed structured JSON-LD entity graph and direct answer definitions to increase AI citation probability."),
                    citation_probability=cp
                ))
            except Exception:
                continue

        blackboard.ai_search_evaluations = parsed_evals

        # Register Claims
        for cl in result.get("claims", []):
            sev_str = str(cl.get("severity", "MEDIUM")).upper()
            sev = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MEDIUM
            blackboard.claim_registry.register_claim(
                agent_id=f"{self.worker_id}_{capability_id}",
                statement=cl.get("statement", "AI search query simulation finding"),
                category=Category.AI_SEARCH,
                severity=sev,
                confidence=float(cl.get("confidence", 0.90)),
                recommendation=cl.get("recommendation", "Optimize answer clarity and JSON-LD schema for AI discovery queries.")
            )

        return result

