"""
On-page answerability simulation.
Labeled SIMULATION_ONLY: infers what an answer engine *could* extract from crawled
pages. Does not invent live ChatGPT/Perplexity citations or search volume.
"""
from typing import List, Dict, Any
from app.domain.models import AiSearchQueryEvaluation, BusinessProfile, PageEvidence


class AIEngineAdapter:
    def __init__(self, engine_name: str):
        self.engine_name = engine_name

    def evaluate_citation_readiness(
        self,
        query: str,
        business_profile: BusinessProfile,
        has_schema: bool,
        has_direct_answers: bool
    ) -> Dict[str, Any]:
        # Structural eligibility only. Never a live citation probability.
        band = "low"
        if has_schema and has_direct_answers:
            band = "medium"
        return {
            "engine": self.engine_name,
            "query": query,
            "citation_probability": None,
            "eligibility_band": band,
            "is_simulation": True
        }


class AISearchSimulationEngine:
    def generate_buyer_query_clusters(self, business_profile: BusinessProfile) -> List[Dict[str, str]]:
        name = business_profile.business_name or "this company"
        niche = (business_profile.niche or business_profile.industry or "").strip()
        return [
            {"cluster": "Navigational", "query": f"What is {name} and what does it do?"},
            {"cluster": "Commercial", "query": f"How much does {name} cost?"},
            {"cluster": "Comparison", "query": f"What are alternatives to {name}" + (f" for {niche}" if niche else "") + "?"},
            {"cluster": "Problem-Aware", "query": f"What problem does {name} solve?"},
            {"cluster": "Trust", "query": f"Is {name} legitimate and what proof does it publish?"},
        ]

    def simulate_queries(
        self,
        business_profile: BusinessProfile,
        pages: List[PageEvidence]
    ) -> List[AiSearchQueryEvaluation]:
        name = business_profile.business_name or ""
        val_prop = (business_profile.value_proposition or "").strip()
        if val_prop.lower() in {"", "value proposition not clearly stated."}:
            val_prop = ""
        h1s = [h.strip() for p in pages for h in (p.h1 or []) if h and h.strip()]
        has_pricing = any("pricing" in (p.url or "").lower() or p.page_type == "pricing" for p in pages)
        has_compare = any(
            any(k in (p.url or "").lower() for k in ("/vs", "compar", "alternativ"))
            for p in pages
        )
        schema_types = {t for p in pages for t in (p.schema_types or [])}
        bodies = " ".join((p.body_text or "")[:800] for p in pages[:4])
        has_pain = bool(
            any(w in bodies.lower() for w in ("problem", "challenge", "struggle", "without", "pain"))
        )
        has_proof = bool(
            any(w in bodies.lower() for w in ("customer", "client", "testimonial", "case study", "iso", "soc 2", "gdpr"))
            or any(t.lower() in {"review", "aggregateofferrating"} for t in schema_types)
        )

        def _eval(q: str, q_type: str, answerable: bool, answer: str, gap: str, score: int) -> AiSearchQueryEvaluation:
            return AiSearchQueryEvaluation(
                query=q,
                question_type=q_type,
                evidence_quality="Good" if answerable and score >= 7 else ("Moderate" if answerable else "Missing"),
                score=score if answerable else 2,
                detected_answer=answer if answerable else "cannot answer from site",
                evidence_snippet=(val_prop or (h1s[0] if h1s else ""))[:120] or None,
                gap_analysis=gap,
                citation_probability=None,
                hallucination_vulnerability_risk="high" if not answerable else "low",
                is_simulated=True,
                provenance_mode="simulation",
            )

        clusters = self.generate_buyer_query_clusters(business_profile)
        evaluations: List[AiSearchQueryEvaluation] = []
        for c in clusters:
            q, q_type = c["query"], c["cluster"]
            if q_type == "Navigational":
                if val_prop or h1s:
                    evaluations.append(_eval(
                        q, q_type, True,
                        val_prop or h1s[0],
                        "Definition exists on-page. This is not a live engine citation.",
                        7 if val_prop else 5,
                    ))
                else:
                    evaluations.append(_eval(q, q_type, False, "", "No H1 or value proposition in the crawl.", 2))
            elif q_type == "Commercial":
                if has_pricing:
                    evaluations.append(_eval(
                        q, q_type, True,
                        "A pricing/plans URL was crawled. Prices themselves were not extracted here.",
                        "Publish actual figures on that URL; this simulation does not invent them.",
                        6,
                    ))
                else:
                    evaluations.append(_eval(q, q_type, False, "", "No pricing/plans URL in the crawl.", 2))
            elif q_type == "Comparison":
                if has_compare:
                    evaluations.append(_eval(
                        q, q_type, True,
                        "A comparison URL was crawled. Rival names must come from that page.",
                        "Do not invent competitors.",
                        5,
                    ))
                else:
                    evaluations.append(_eval(q, q_type, False, "", "No comparison/alternatives URL in the crawl.", 2))
            elif q_type == "Problem-Aware":
                if has_pain or val_prop:
                    evaluations.append(_eval(
                        q, q_type, True,
                        val_prop or "Pain language appears in body copy.",
                        "Quote the page; do not invent a generic bottleneck story.",
                        5 if has_pain else 4,
                    ))
                else:
                    evaluations.append(_eval(q, q_type, False, "", "No problem/pain paragraph crawled.", 2))
            else:
                if has_proof or "Organization" in schema_types:
                    evaluations.append(_eval(
                        q, q_type, True,
                        "Trust or Organization signals were observed (schema or proof language).",
                        "This is not a live compliance verification.",
                        5,
                    ))
                else:
                    evaluations.append(_eval(q, q_type, False, "", "No proof, certification, or Organization schema crawled.", 2))
        return evaluations
