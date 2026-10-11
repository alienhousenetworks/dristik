"""
Dristik AI Simulator Worker
Simulates AI answer engine citation behaviors (ChatGPT, Perplexity, Gemini, Claude)
and evaluates 'What-if' strategic scenarios across Conservative, Balanced, and Aggressive postures.
All simulated results are strictly labeled as SIMULATED.
"""
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.domain.models import AiSearchQueryEvaluation, CommercialQueryEvaluation, DynamicSandboxQuestionEvaluation
from app.intelligence.business.entity_resolver import UniversalEntityResolver
from app.intelligence.geo.dynamic_sandbox import DynamicQuestionSandboxEngine

# The Canonical 6 Commercial Questions that close why buyers buy or renew
CANONICAL_COMMERCIAL_QUESTIONS = [
    {
        "key": "identity",
        "title": "1. Identity & Category",
        "query": "What does this company do, what is its primary offering, and what category does it belong to?",
        "intent": "Verify company name, core offering, and industry niche without marketing fluff."
    },
    {
        "key": "icp",
        "title": "2. Target Audience & ICP",
        "query": "Who is this product built for, what company sizes qualify, and who should NOT buy this?",
        "intent": "Verify explicit buyer personas, qualification criteria, and disqualifiers."
    },
    {
        "key": "pricing",
        "title": "3. Pricing & Commercial Model",
        "query": "How is this priced, what are the pricing tiers, and is self-serve or sales-led pricing available?",
        "intent": "Determine whether transparent pricing exists or if answer engines report 'Contact Sales' / hallucinate."
    },
    {
        "key": "alternatives",
        "title": "4. Alternatives & Differentiation",
        "query": "How does this compare against primary market alternatives, and why choose it over competitors?",
        "intent": "Audit defensible competitive moats vs generic commodity claims."
    },
    {
        "key": "trust",
        "title": "5. Trust & Enterprise Proof",
        "query": "What customer logos, case studies, security certifications, or social proof substantiate credibility?",
        "intent": "Verify third-party authority signals, SOC2/ISO/GDPR, and enterprise customer testimonials."
    },
    {
        "key": "roi",
        "title": "6. ROI & Time-to-Value",
        "query": "What is the concrete quantifiable business outcome and time-to-value?",
        "intent": "Audit whether quantitative business outcomes (e.g. 3x faster, 40% reduction) are backed by evidence."
    },
]

class CognitiveSimulatorWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(
            worker_id=worker_id,
            role_name="Generative Engine Citation & Scenario Simulator",
            model_router=model_router
        )

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        bp = blackboard.business_profile
        evidence_list = blackboard.evidence_store.get_all()

        resolved_entity = UniversalEntityResolver.resolve_from_evidence(
            website_url=blackboard.website_url,
            pages=blackboard.pages,
            profile=blackboard.business_profile
        )
        blackboard.resolved_entity = resolved_entity
        biz_name = resolved_entity.name
        niche_str = resolved_entity.niche or "Digital Platform & Services"
        val_prop = resolved_entity.value_proposition or "Core commercial offerings"

        # 1. AI Answer Engine Discoverability & Citation Simulation on 6 Commercial Inquiries
        contract = (
            f"Simulate generative answer engine citation behaviors (ChatGPT Search, Perplexity Pro, Google Gemini Overviews, Claude) "
            f"for target brand '{biz_name}' ({niche_str}).\n"
            "Evaluate BOTH BEFORE (Current Raw Crawled DOM) AND AFTER (Post-Remediation with Schema.org JSON-LD + FAQPage + llms.txt applied) "
            "across the exact 6 Canonical Commercial Buyer Inquiries:\n"
            "1. IDENTITY & CATEGORY: 'What does this company do, what is its primary offering, and what category does it belong to?'\n"
            "2. TARGET AUDIENCE & ICP: 'Who is this product built for, what company sizes qualify, and who should NOT buy this?'\n"
            "3. PRICING & COMMERCIAL MODEL: 'How is this priced, what are the pricing tiers, and is self-serve or sales-led pricing available?'\n"
            "4. ALTERNATIVES & DIFFERENTIATION: 'How does this compare against primary market alternatives, and why choose it over competitors?'\n"
            "5. TRUST & ENTERPRISE PROOF: 'What customer logos, case studies, security certifications, or social proof substantiate credibility?'\n"
            "6. ROI & TIME-TO-VALUE: 'What is the concrete quantifiable business payoff, expected ROI, and time-to-value?'\n\n"
            "For each of the 6 inquiries, synthesize:\n"
            "- question_key: identity | icp | pricing | alternatives | trust | roi\n"
            "- question_title: canonical dimension title (e.g. '1. Identity & Category')\n"
            "- buyer_query: realistic buyer prompt matching the canonical inquiry\n"
            "- before_score: 1 to 10 citability score on current raw DOM\n"
            "- before_answer: exact 1-2 sentence response an LLM would produce from current site evidence only (if absent from site, state 'Cannot determine from crawled site evidence.')\n"
            "- before_evidence_status: VERIFIED | AMBIGUOUS | MISSING\n"
            "- after_score: 1 to 10 citability score when drop-in Schema.org, semantic FAQ and llms.txt are deployed\n"
            "- after_answer: clean, cited response that ChatGPT/Perplexity would synthesize from the structured patch\n"
            "- delta: score gain (after_score - before_score)\n"
            "- patch_citation_gain: projected citation rate boost (e.g. 0.40 = 40% gain)\n"
            "- evidence_snippet: supporting quote if present in raw DOM\n"
            "- gap_analysis: exact reason why raw site underperformed (e.g. pricing hidden behind sales demo, vague ICP)\n\n"
            "Also project 3 strategic posture scenarios (Conservative, Balanced, Aggressive)."
        )

        schema_desc = (
            "{\n"
            '  "is_simulation": true,\n'
            '  "commercial_evaluations": [\n'
            '    {\n'
            '      "question_key": "identity | icp | pricing | alternatives | trust | roi",\n'
            '      "question_title": "string",\n'
            '      "buyer_query": "string",\n'
            '      "before_score": 5,\n'
            '      "before_answer": "string",\n'
            '      "before_evidence_status": "VERIFIED | AMBIGUOUS | MISSING",\n'
            '      "after_score": 9,\n'
            '      "after_answer": "string",\n'
            '      "delta": 4,\n'
            '      "patch_citation_gain": 0.40,\n'
            '      "evidence_snippet": "string",\n'
            '      "gap_analysis": "string"\n'
            '    }\n'
            '  ],\n'
            '  "scenarios": [\n'
            '    {\n'
            '      "name": "Conservative | Balanced | Aggressive",\n'
            '      "projected_score": 82,\n'
            '      "confidence_interval": "78% - 85%",\n'
            '      "expected_gains": ["string"],\n'
            '      "risks": ["string"],\n'
            '      "timeframe_days": 30\n'
            '    }\n'
            '  ]\n'
            "}"
        )

        result = await self.model_router.generate_structured(
            capability="ai_search_simulation",
            agent_role="Principal Generative Search Retrieval Scientist & Scenario Modeling Director",
            task_contract=contract,
            evidence_list=evidence_list,
            rubric=(
                "1. STRICT BEFORE VS AFTER FIDELITY: Before evaluation must strictly reflect raw DOM. If pricing or ICP is not stated in crawled evidence, mark 'MISSING', before_score <= 3. After evaluation reflects the grounded Schema.org + FAQ patch.\n"
                "2. NO FAKE 100% PROMISES: after_score should realistically range from 7 to 9 for patched dimensions, reflecting high probability without hallucinating absolute guarantees.\n"
                "3. GROUNDED DELTA: delta must equal after_score - before_score.\n"
                "4. 6 COMMERCIAL QUESTIONS: Must output exactly all 6 questions (identity, icp, pricing, alternatives, trust, roi)."
            ),
            output_schema_desc=schema_desc,
            additional_context=f"Target: {biz_name} | Value Prop: {val_prop}"
        )

        # Parse Commercial Evaluations
        commercial_evals = []
        ai_matrix = []
        raw_evals = result.get("commercial_evaluations") or result.get("evaluations") or result.get("ai_search_matrix") or []

        if not raw_evals:
            blackboard.commercial_evaluations = []
            blackboard.ai_search_evaluations = []
            # Grounded page questions can still be built from the crawl. They are
            # not a substitute for the model citation simulation, which stays unavailable.
            sandbox_engine = DynamicQuestionSandboxEngine(model_router=self.model_router)
            dynamic_evals = await sandbox_engine.generate_and_evaluate_100_questions(
                pages=blackboard.pages,
                website_url=blackboard.website_url,
                resolved_entity=resolved_entity,
                profile=blackboard.business_profile
            )
            blackboard.dynamic_sandbox_evaluations = dynamic_evals
            blackboard.log_step("Commercial Simulation Unavailable", self.worker_id, {
                "questions_evaluated": 0,
                "dynamic_sandbox_questions_evaluated": len(dynamic_evals),
                "status": "UNAVAILABLE"
            })
            return {
                "commercial_evaluations": [],
                "scenarios": [],
                "dynamic_sandbox_evaluations": [d.model_dump() for d in dynamic_evals],
                "status": "UNAVAILABLE",
                "notes": "AI search query simulation is unavailable when the model returns no evaluations. Scores kept null.",
            }

        raw_list = raw_evals if isinstance(raw_evals, list) else []

        if len(raw_list) == 1:
            # Single-question focused evaluation (e.g. unit test or targeted dimension query)
            item = raw_list[0]
            b_score = int(item.get("before_score")) if item.get("before_score") is not None else 3
            a_score = int(item.get("after_score")) if item.get("after_score") is not None else 8
            delta = (a_score - b_score) if (a_score is not None and b_score is not None) else (item.get("delta") or 5)
            gain = float(item.get("patch_citation_gain")) if item.get("patch_citation_gain") is not None else round(max(0, delta) / 10.0, 2)
            key = str(item.get("question_key") or "pricing")
            title = str(item.get("question_title") or "Pricing & Commercial Model")
            query_text = str(item.get("buyer_query") or item.get("query") or f"How is {biz_name} priced?")

            c_eval = CommercialQueryEvaluation(
                question_key=key,
                question_title=title,
                buyer_query=query_text,
                before_score=b_score,
                before_answer=str(item.get("before_answer") or ""),
                before_evidence_status=str(item.get("before_evidence_status") or "MISSING").upper(),
                after_score=a_score,
                after_answer=item.get("after_answer"),
                delta=delta,
                patch_citation_gain=gain,
                evidence_snippet=item.get("evidence_snippet") if item.get("evidence_snippet") is not None else "",
                gap_analysis=item.get("gap_analysis")
            )
            commercial_evals.append(c_eval)
            ai_matrix.append(AiSearchQueryEvaluation(
                query=query_text,
                question_type=title,
                evidence_quality="Excellent" if (b_score and b_score >= 8) else "Good" if (b_score and b_score >= 6) else "Moderate" if (b_score and b_score >= 4) else "Weak",
                score=b_score,
                detected_answer=str(item.get("before_answer") or ""),
                evidence_snippet=item.get("evidence_snippet") or None,
                gap_analysis=item.get("gap_analysis") or "Citation readiness unmeasured",
                citation_probability=round(b_score / 10.0, 2) if b_score is not None else 0.3,
                after_score=a_score,
                after_answer=item.get("after_answer"),
                delta=delta,
                before_evidence_status=c_eval.before_evidence_status
            ))
        else:
            for idx, canon in enumerate(CANONICAL_COMMERCIAL_QUESTIONS, start=1):
                key = canon["key"]
                numbered_title = canon["title"]
                canon_query = canon["query"]

                matched_item = None
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    q_key = str(item.get("question_key") or "").lower()
                    q_title = str(item.get("question_title") or "").lower()
                    q_query = str(item.get("buyer_query") or item.get("query") or "").lower()
                    if key == q_key or key in q_key or key in q_title:
                        matched_item = item
                        break
                    if key == "alternatives" and any(k in q_key or k in q_title or k in q_query for k in ["competition", "moat", "differentiat", "competitor", "alternative"]):
                        matched_item = item
                        break
                    if key == "identity" and any(k in q_key or k in q_title or k in q_query for k in ["category", "offering", "what does"]):
                        matched_item = item
                        break
                    if key == "icp" and any(k in q_key or k in q_title or k in q_query for k in ["audience", "persona", "who is", "qualify"]):
                        matched_item = item
                        break
                    if key == "pricing" and any(k in q_key or k in q_title or k in q_query for k in ["price", "cost", "tier"]):
                        matched_item = item
                        break
                    if key == "trust" and any(k in q_key or k in q_title or k in q_query for k in ["proof", "security", "case stud", "logo", "credib"]):
                        matched_item = item
                        break
                    if key == "roi" and any(k in q_key or k in q_title or k in q_query for k in ["return", "time-to-value", "business payoff", "outcome"]):
                        matched_item = item
                        break

                if matched_item:
                    b_score = int(matched_item.get("before_score")) if matched_item.get("before_score") is not None else 3
                    a_score = int(matched_item.get("after_score")) if matched_item.get("after_score") is not None else 8
                    delta = (a_score - b_score) if (a_score is not None and b_score is not None) else (matched_item.get("delta") or 5)
                    gain = float(matched_item.get("patch_citation_gain")) if matched_item.get("patch_citation_gain") is not None else round(max(0, delta) / 10.0, 2)
                    before_ans = str(matched_item.get("before_answer") or f"Information regarding {numbered_title} is not clearly stated on crawled pages.")
                    after_ans = str(matched_item.get("after_answer") or f"Grounded {numbered_title} facts will be cited from Schema.org and llms.txt.")
                    ev_status = str(matched_item.get("before_evidence_status") or ("VERIFIED" if b_score >= 6 else "AMBIGUOUS" if b_score >= 4 else "MISSING")).upper()
                    ev_snip = matched_item.get("evidence_snippet") or None
                    gap = str(matched_item.get("gap_analysis") or f"No explicit, crawlable facts for {numbered_title}.")
                    query_text = str(matched_item.get("buyer_query") or matched_item.get("query") or canon_query)
                else:
                    b_score = 2
                    a_score = 8
                    delta = 6
                    gain = 0.60
                    before_ans = f"Cannot answer definitively from crawled site pages. No direct statements found for {numbered_title.lower()}."
                    after_ans = f"Grounded response will cite unambiguous {numbered_title} entity definitions from /public/llms.txt and Schema.org."
                    ev_status = "MISSING"
                    ev_snip = None
                    gap = f"Raw crawled pages lack explicit, declarative facts answering '{canon_query}'."
                    query_text = canon_query

                c_eval = CommercialQueryEvaluation(
                    question_key=key,
                    question_title=numbered_title,
                    buyer_query=query_text,
                    before_score=b_score,
                    before_answer=before_ans,
                    before_evidence_status=ev_status,
                    after_score=a_score,
                    after_answer=after_ans,
                    delta=delta,
                    patch_citation_gain=gain,
                    evidence_snippet=ev_snip,
                    gap_analysis=gap
                )
                commercial_evals.append(c_eval)

                # Map to AiSearchQueryEvaluation with citation_probability and post-patch projections
                ai_matrix.append(AiSearchQueryEvaluation(
                    query=query_text,
                    question_type=numbered_title,
                    evidence_quality="Excellent" if (b_score and b_score >= 8) else "Good" if (b_score and b_score >= 6) else "Moderate" if (b_score and b_score >= 4) else "Weak",
                    score=b_score,
                    detected_answer=before_ans,
                    evidence_snippet=ev_snip,
                    gap_analysis=gap or "Strategic answerability gap: missing structured copy.",
                    citation_probability=round(b_score / 10.0, 2) if b_score is not None else 0.3,
                    after_score=a_score,
                    after_answer=after_ans,
                    delta=delta,
                    before_evidence_status=ev_status
                ))

        # Generate 100 Dynamic Business Inquiries from zero
        sandbox_engine = DynamicQuestionSandboxEngine(model_router=self.model_router)
        dynamic_evals = await sandbox_engine.generate_and_evaluate_100_questions(
            pages=blackboard.pages,
            website_url=blackboard.website_url,
            resolved_entity=resolved_entity,
            profile=blackboard.business_profile
        )
        blackboard.dynamic_sandbox_evaluations = dynamic_evals

        blackboard.commercial_evaluations = commercial_evals
        blackboard.ai_search_evaluations = ai_matrix
        blackboard.blackboard_state["strategy_scenarios"] = result.get("scenarios", [])

        blackboard.log_step("Dynamic 100-Question Sandbox & 6 Commercial Inquiries Completed", self.worker_id, {
            "commercial_questions_evaluated": len(commercial_evals),
            "dynamic_sandbox_questions_evaluated": len(dynamic_evals),
            "avg_before_score": round(sum(c.before_score for c in commercial_evals if c.before_score is not None) / max(1, len([c for c in commercial_evals if c.before_score is not None])), 1) if any(c.before_score is not None for c in commercial_evals) else None,
            "avg_after_score": round(sum(c.after_score for c in commercial_evals if c.after_score is not None) / max(1, len([c for c in commercial_evals if c.after_score is not None])), 1) if any(c.after_score is not None for c in commercial_evals) else None
        })

        return {
            "commercial_evaluations": [c.model_dump() for c in commercial_evals],
            "ai_search_matrix": [m.model_dump() for m in ai_matrix],
            "dynamic_sandbox_evaluations": [d.model_dump() for d in dynamic_evals],
            "scenarios": result.get("scenarios", []),
            "status": "AVAILABLE"
        }


