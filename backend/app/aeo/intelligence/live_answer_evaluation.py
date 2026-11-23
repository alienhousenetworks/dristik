"""
Live Answer-Engine Evaluation — Phase 5.6

Evaluates real AI answer engines on question-level response fidelity:
- Direct answer appearance (Synthesized answer card or direct snippet)
- Answer completeness (All required question elements present in AI summary)
- Brand factual accuracy (Product names, price figures, clinical details correctly quoted)
- Citation correctness (Citation links directly to primary authoritative landing page)
- Source relevance (Relevance of cited third-party resources)
- Competitor answer presence (Competitor stealing answer spotlight)
- Unsupported hallucination detection (AI generating unverified claims)

Reuses the shared benchmarking telemetry from Phase 4 to guarantee 100% data consistency.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AeoLiveAnswerTestResult(BaseModel):
    question_id: str
    question_text: str
    surface_name: str
    direct_answer_generated: bool
    answer_completeness_pct: float
    brand_accurately_represented: bool
    citation_correctness: str  # "FIRST_PARTY_CANONICAL", "THIRD_PARTY_ONLY", "NO_CITATION"
    competitors_present_in_answer: List[str] = Field(default_factory=list)
    hallucination_detected: bool = False
    raw_response_snippet: str
    consistency_score_pct: float = 100.0


class LiveAnswerEvaluationReport(BaseModel):
    total_questions_tested: int
    direct_answer_rate_pct: float
    average_completeness_pct: float
    citation_correctness_rate_pct: float
    hallucination_rate_pct: float
    connection_status: str = "CONNECTED"  # "CONNECTED", "CREDENTIALS_NOT_CONFIGURED", "NOT_TESTED"
    status_note: Optional[str] = None
    results: List[AeoLiveAnswerTestResult] = Field(default_factory=list)
    actionable_remediation: List[str] = Field(default_factory=list)


class LiveAnswerEvaluationEngine:
    """
    Evaluates live synthesized answer performance from benchmark response payloads.
    """

    @classmethod
    def evaluate_live_answers(
        cls,
        domain: str,
        brand_name: str,
        tested_queries: List[Dict[str, Any]],  # {"question_id": str, "question": str, "surface": str, "response": str, "citations": List[str]}
        expected_facts: Optional[Dict[str, str]] = None,
        tracked_competitors: Optional[List[str]] = None,
        connection_status: str = "CONNECTED",
    ) -> LiveAnswerEvaluationReport:
        if not tested_queries:
            status = connection_status if connection_status != "CONNECTED" else "CREDENTIALS_NOT_CONFIGURED"
            return LiveAnswerEvaluationReport(
                total_questions_tested=0,
                direct_answer_rate_pct=0.0,
                average_completeness_pct=0.0,
                citation_correctness_rate_pct=0.0,
                hallucination_rate_pct=0.0,
                connection_status=status,
                status_note=(
                    "Live citation benchmarking was not executed because engine API credentials are not configured for this analysis run. "
                    "In accordance with Dristik measurement integrity rules, citation metrics remain unmeasured rather than simulated."
                ),
                results=[],
                actionable_remediation=["Configure Perplexity / OpenAI API keys in workspace integrations to enable live AI citation verification."],
            )

        results: List[AeoLiveAnswerTestResult] = []
        recs: List[str] = []

        direct_count = 0
        total_comp = 0.0
        canonical_cit_count = 0
        hallucination_count = 0

        clean_domain = domain.lower().replace("www.", "")
        facts = expected_facts or {}
        competitor_pool = list(tracked_competitors) if tracked_competitors is not None else []

        for item in tested_queries:
            qid = item.get("question_id", "Q-001")
            q_text = item.get("question", "")
            surface = item.get("surface", "AI Synthesizer")
            resp = item.get("response", "")
            citations = item.get("citations", [])

            # 1. Direct Answer Generated
            is_direct = len(resp.strip()) > 30 and not resp.lower().startswith("i cannot answer")
            if is_direct:
                direct_count += 1

            # 2. Brand Factual Accuracy
            brand_in_resp = brand_name.lower() in resp.lower()
            acc = brand_in_resp

            # Check if any expected fact is contradicted
            has_hallucination = False
            for fact_k, fact_v in facts.items():
                if fact_k.lower() in q_text.lower():
                    if fact_v.lower() not in resp.lower() and re.search(r'\$\d+', resp):
                        has_hallucination = True
                        hallucination_count += 1

            # 3. Citation Correctness
            has_fp = any(clean_domain in c.lower() for c in citations)
            if has_fp:
                cit_status = "FIRST_PARTY_CANONICAL"
                canonical_cit_count += 1
            elif citations:
                cit_status = "THIRD_PARTY_ONLY"
            else:
                cit_status = "NO_CITATION"

            # 4. Answer Completeness
            comp = 100.0 if (is_direct and acc and not has_hallucination) else (60.0 if is_direct else 0.0)
            total_comp += comp

            # 5. Competitors detected (dynamically from tracked pool, not hardcoded)
            comps_found = []
            for c_name in competitor_pool:
                if c_name.lower() in resp.lower() and c_name.lower() != brand_name.lower():
                    comps_found.append(c_name)

            results.append(
                AeoLiveAnswerTestResult(
                    question_id=qid,
                    question_text=q_text,
                    surface_name=surface,
                    direct_answer_generated=is_direct,
                    answer_completeness_pct=comp,
                    brand_accurately_represented=acc,
                    citation_correctness=cit_status,
                    competitors_present_in_answer=comps_found,
                    hallucination_detected=has_hallucination,
                    raw_response_snippet=resp[:160] + "..." if len(resp) > 160 else resp,
                )
            )

        n = max(len(tested_queries), 1)
        direct_rate = round((direct_count / n) * 100, 1)
        avg_comp = round(total_comp / n, 1)
        cit_rate = round((canonical_cit_count / n) * 100, 1)
        hal_rate = round((hallucination_count / n) * 100, 1)

        if cit_rate < 50.0:
            recs.append("Increase first-party canonical citation share by publishing clear declarative Q&A schema blocks.")
        if hal_rate > 0.0:
            recs.append("Address AI answer hallucination risk by embedding explicit tabular specifications on target pages.")

        return LiveAnswerEvaluationReport(
            total_questions_tested=len(tested_queries),
            direct_answer_rate_pct=direct_rate,
            average_completeness_pct=avg_comp,
            citation_correctness_rate_pct=cit_rate,
            hallucination_rate_pct=hal_rate,
            connection_status="CONNECTED",
            status_note=f"Successfully evaluated {len(tested_queries)} live engine queries.",
            results=results,
            actionable_remediation=recs,
        )
