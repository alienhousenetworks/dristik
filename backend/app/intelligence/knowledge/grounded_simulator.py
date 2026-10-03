"""
Dristik KIE — Phase 5: Grounded Answer Simulator & Claim-Level Verifier
Executes the controlled answer simulation pipeline:
  1. Question → Query Planner → Hybrid Retriever → Top-5 Evidence Chunks
  2. Synthesize a candidate answer constrained to retrieved evidence
  3. Decompose answer into atomic factual claims
  4. Verify each claim against retrieved evidence
  5. Compute Grounding Ratio and Answer Risk

IMPORTANT DEFINITION — printed clearly for auditors:
"A Grounded Answer Simulation is a controlled laboratory evaluation testing whether
 an answer engine COULD construct a defensible, hallucination-free answer from
 the evidence available on the site. It does NOT reproduce or claim to replicate
 the proprietary internal retrieval/ranking systems of ChatGPT, Perplexity,
 Claude, or Gemini."
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.intelligence.knowledge.primitives import (
    AtomicClaim,
    ClaimGroundingResult,
    FiveDimensionAiVisibility,
    GroundedAnswerSimulation,
    KieAnswerRisk,
    KieEvidenceState,
    KieEvidenceStrength,
)
from app.intelligence.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph
from app.intelligence.retrieval.hybrid_retriever import (
    HybridRetriever,
    QueryPlanner,
    RetrievedEvidenceChunk,
)


SIMULATION_DISCLAIMER = (
    "Grounded Answer Simulation: a controlled test of answer defensibility from "
    "first-party evidence. Does NOT reproduce proprietary ChatGPT, Perplexity, "
    "Claude, or Gemini retrieval systems."
)


# ─────────────────────────────────────────────────────────────────────────────
# Claim Sentence Splitter
# ─────────────────────────────────────────────────────────────────────────────

def _decompose_into_claims(answer_text: str) -> List[str]:
    """
    Decompose a synthesized answer into individual claim sentences.
    Uses sentence boundaries and semi-colon splits.
    """
    raw = re.split(r"(?<=[.!?;])\s+", answer_text.strip())
    return [s.strip() for s in raw if len(s.strip()) > 15]


# ─────────────────────────────────────────────────────────────────────────────
# Claim Verifier
# ─────────────────────────────────────────────────────────────────────────────

def _verify_claim_against_evidence(
    claim_sentence: str,
    evidence_chunks: List[RetrievedEvidenceChunk],
) -> ClaimGroundingResult:
    """
    Verifies one atomic claim against the retrieved evidence chunks using:
    1. Token overlap between claim and evidence (recall-oriented)
    2. High-signal keyword exact matching (precision-oriented)
    """
    claim_tokens = set(re.sub(r"[^\w\s]", " ", claim_sentence.lower()).split())
    claim_tokens -= {"the", "a", "an", "is", "are", "and", "or", "for", "of", "with"}

    best_score = 0.0
    best_snippet: Optional[str] = None
    best_url: Optional[str] = None

    for chunk in evidence_chunks:
        ev = chunk.claim.evidence
        ev_text = ev.exact_sentence if ev else f"{chunk.claim.predicate} {chunk.claim.object}"
        ev_tokens = set(re.sub(r"[^\w\s]", " ", ev_text.lower()).split())

        # Token overlap ratio
        overlap = len(claim_tokens & ev_tokens) / max(1, len(claim_tokens))

        # Boost for exact multi-word phrase match
        phrase_boost = 0.0
        claim_lower = claim_sentence.lower()
        for tok in sorted(ev_tokens, key=len, reverse=True):
            if len(tok) > 5 and tok in claim_lower:
                phrase_boost = min(0.4, phrase_boost + 0.1)

        score = overlap + phrase_boost

        if score > best_score:
            best_score = score
            best_snippet = ev_text[:200]
            best_url = ev.url if ev else None

    if best_score >= 0.45:
        return ClaimGroundingResult(
            claim_text=claim_sentence,
            status="SUPPORTED",
            evidence_snippet=best_snippet,
            evidence_url=best_url,
            confidence=min(1.0, best_score),
        )
    elif best_score >= 0.20:
        return ClaimGroundingResult(
            claim_text=claim_sentence,
            status="PARTIALLY_SUPPORTED",
            evidence_snippet=best_snippet,
            evidence_url=best_url,
            confidence=best_score,
        )
    else:
        return ClaimGroundingResult(
            claim_text=claim_sentence,
            status="UNSUPPORTED",
            evidence_snippet=None,
            evidence_url=None,
            confidence=0.0,
        )


from app.intelligence.knowledge.evidence_sufficiency import (
    EvidenceAssessment,
    EvidenceSufficiencyEvaluator,
)
from app.intelligence.retrieval.hybrid_retriever import QueryIntent


# ─────────────────────────────────────────────────────────────────────────────
# Answer Synthesizer (from Evidence)
# ─────────────────────────────────────────────────────────────────────────────

def _synthesize_from_evidence(
    question: str,
    brand: str,
    plan: Any,
    evidence_chunks: List[RetrievedEvidenceChunk],
    assessment: EvidenceAssessment,
) -> str:
    """
    Synthesizes an authoritative candidate answer strictly from relevance-gated evidence.
    If evidence is missing or insufficient, produces an explicit gap statement rather
    than concatenating irrelevant marketing paragraphs.
    """
    if not evidence_chunks or assessment.status == "INSUFFICIENT":
        if plan.intent == QueryIntent.COMMERCIAL:
            return f"Pricing information, tier rates, and commercial packages for {brand} are not published on crawled website pages."
        elif plan.intent == QueryIntent.COMPLIANCE:
            return f"Security compliance certifications (such as SOC 2, ISO 27001, or HIPAA) are not published on crawled pages for {brand}."
        elif plan.intent == QueryIntent.PROOF:
            return f"Customer logos, verified client case studies, and quantified ROI results are not published on crawled pages for {brand}."
        elif plan.intent == QueryIntent.ONBOARDING:
            return f"Support SLAs, guaranteed ticket response times, and onboarding procedures for {brand} are not disclosed on crawled pages."
        elif plan.intent == QueryIntent.COMPETITIVE:
            return f"Competitive comparisons, alternative benchmarking, and explicit moat claims are not published on crawled pages for {brand}."
        elif plan.intent == QueryIntent.ICP:
            return f"Explicit buyer criteria and target audience personas for {brand} are not declared on crawled pages."
        return f"Information regarding this inquiry was not discovered in crawled website evidence for {brand}."

    # Substantive synthesis from qualified evidence
    sentences: List[str] = []
    seen = set()
    for chunk in evidence_chunks[:2]:
        ev = chunk.claim.evidence
        sentence = ev.exact_sentence.strip() if ev and ev.exact_sentence else f"{chunk.claim.predicate} {chunk.claim.object}"
        sentence = sentence.rstrip(".")
        if sentence and sentence.lower() not in seen:
            seen.add(sentence.lower())
            sentences.append(sentence)

    primary = ". ".join(sentences) + "."
    if not primary.strip("."):
        return f"Insufficient evidence found to answer: {question}"

    base_answer = f"According to {brand}'s crawled pages: \"{primary}\""
    if assessment.status == "PARTIAL" and assessment.missing_aspects:
        base_answer += f" However, crawled evidence does not provide details for: {', '.join(assessment.missing_aspects)}."

    return base_answer[:500]


# ─────────────────────────────────────────────────────────────────────────────
# Grounded Answer Simulator
# ─────────────────────────────────────────────────────────────────────────────

class GroundedAnswerSimulator:
    """
    Phase 5 KIE component.

    For each question:
      Question → Query Planner → Hybrid Retriever → Evidence Sufficiency → Synthesize → Decompose → Verify → Grade

    Returns a GroundedAnswerSimulation with per-claim verification and grounding ratio.
    """

    SIMULATION_DISCLAIMER = SIMULATION_DISCLAIMER

    def __init__(self, graph: WebsiteKnowledgeGraph, model_router=None):
        self.graph = graph
        self.retriever = HybridRetriever(graph)
        self.model_router = model_router  # Optional: plug in LLM for richer synthesis

    def simulate(
        self,
        question_id: str,
        question: str,
    ) -> GroundedAnswerSimulation:
        plan = QueryPlanner.plan(question)
        evidence_chunks = self.retriever.retrieve(question, plan)
        assessment = EvidenceSufficiencyEvaluator.evaluate(
            question=question,
            evidence_chunks=evidence_chunks,
            brand=self.graph.brand,
        )

        candidate_answer = _synthesize_from_evidence(
            question=question,
            brand=self.graph.brand,
            plan=plan,
            evidence_chunks=evidence_chunks,
            assessment=assessment,
        )

        if assessment.status == "INSUFFICIENT" or not evidence_chunks:
            grounding_ratio = 0.0
            grounding_results = []
            answer_risk = KieAnswerRisk.HIGH
        else:
            raw_claims = _decompose_into_claims(candidate_answer)
            grounding_results = [
                _verify_claim_against_evidence(rc, evidence_chunks)
                for rc in raw_claims
            ] if raw_claims else []

            total = len(grounding_results)
            supported = sum(1 for r in grounding_results if r.status == "SUPPORTED")
            partial = sum(1 for r in grounding_results if r.status == "PARTIALLY_SUPPORTED")

            base_ratio = round((supported + 0.5 * partial) / max(1, total), 3)
            # Factor in question aspect coverage so partial questions don't claim 1.0 grounding
            grounding_ratio = round(base_ratio * assessment.coverage_ratio, 3)

            answer_risk = self._compute_answer_risk(
                plan=plan,
                evidence_chunks=evidence_chunks,
                grounding_ratio=grounding_ratio,
                assessment=assessment,
            )

        return GroundedAnswerSimulation(
            question_id=question_id,
            candidate_answer=candidate_answer,
            claim_decomposition=grounding_results,
            grounding_ratio=grounding_ratio,
            retrieval_evidence_count=len(evidence_chunks),
            answer_risk=answer_risk,
            assessment_status=assessment.status,
            missing_aspects=assessment.missing_aspects,
            supported_aspects=assessment.supported_aspects,
        )

    def _compute_answer_risk(
        self,
        plan,
        evidence_chunks: List[RetrievedEvidenceChunk],
        grounding_ratio: float,
        assessment: Optional[EvidenceAssessment] = None,
    ) -> KieAnswerRisk:
        """
        Risk is HIGH when high-intent commercial/compliance query has no or weak evidence,
        or when contradictory evidence is discovered.
        Risk is MEDIUM for partial evidence or technical gaps.
        Risk is LOW for queries with strong first-party support.
        """
        if assessment and assessment.status == "CONFLICTING":
            return KieAnswerRisk.HIGH

        if not evidence_chunks or (assessment and assessment.status == "INSUFFICIENT") or grounding_ratio < 0.25:
            return KieAnswerRisk.HIGH

        if grounding_ratio < 0.65 or (assessment and assessment.status == "PARTIAL"):
            return KieAnswerRisk.MEDIUM

        return KieAnswerRisk.LOW


# ─────────────────────────────────────────────────────────────────────────────
# AI Visibility Index Calculator
# ─────────────────────────────────────────────────────────────────────────────

class AiVisibilityIndexCalculator:
    """
    Computes the 5 independent diagnostic dimensions of AI Visibility.
    Dimensions are NOT combined with arbitrary equal weighting.
    Any aggregate_index is explicitly documented and configurable.
    """

    def compute(
        self,
        graph: WebsiteKnowledgeGraph,
        simulations: List[GroundedAnswerSimulation],
    ) -> FiveDimensionAiVisibility:
        return FiveDimensionAiVisibility(
            knowledge_coverage=self._knowledge_coverage(graph),
            retrieval_coverage=self._retrieval_coverage(simulations),
            evidence_quality=self._evidence_quality(graph),
            answer_grounding=self._answer_grounding(simulations),
            citation_quality=self._citation_quality(simulations),
            aggregate_index=None,  # Never hardcoded; caller may compute with named weighting profile
            weighting_profile="independent",
        )

    def _knowledge_coverage(self, graph: WebsiteKnowledgeGraph) -> float:
        """% of the 10 KIE facets for which at least 2 claims exist."""
        FACET_KEYWORDS = [
            ["identity", "mission", "company", "founded", "headquarter"],
            ["icp", "customer", "audience", "enterprise", "startup", "segment"],
            ["pricing", "cost", "plan", "subscription", "billing"],
            ["feature", "capability", "workflow", "automat", "dashboard"],
            ["api", "integration", "tech", "stack", "sdk", "kubernetes"],
            ["competitor", "alternative", "vs ", "compare", "differ"],
            ["soc", "gdpr", "security", "certif", "compliance", "encrypt"],
            ["case study", "customer story", "roi", "result", "outcome"],
            ["onboarding", "support", "implementation", "sla", "success"],
            ["demo", "trial", "contact", "purchase", "get started"],
        ]
        covered = 0
        for keywords in FACET_KEYWORDS:
            hits = [c for c in graph.claims if any(k in f"{c.predicate} {c.object}".lower() for k in keywords)]
            if len(hits) >= 2:
                covered += 1
        return round(covered / len(FACET_KEYWORDS) * 100, 1)

    def _retrieval_coverage(self, simulations: List[GroundedAnswerSimulation]) -> float:
        if not simulations:
            return 0.0
        with_evidence = sum(1 for s in simulations if s.retrieval_evidence_count > 0)
        return round(with_evidence / len(simulations) * 100, 1)

    def _evidence_quality(self, graph: WebsiteKnowledgeGraph) -> float:
        """% of claims with HIGH-strength evidence and FACT/CAPABILITY type."""
        from app.intelligence.knowledge.primitives import KieClaimType, KieEvidenceStrength
        if not graph.claims:
            return 0.0
        high_quality = sum(
            1 for c in graph.claims
            if c.evidence_strength == KieEvidenceStrength.HIGH
            and c.claim_type in (KieClaimType.FACT, KieClaimType.CAPABILITY)
        )
        return round(high_quality / len(graph.claims) * 100, 1)

    def _answer_grounding(self, simulations: List[GroundedAnswerSimulation]) -> float:
        if not simulations:
            return 0.0
        avg_grounding = sum(s.grounding_ratio for s in simulations) / len(simulations)
        return round(avg_grounding * 100, 1)

    def _citation_quality(self, simulations: List[GroundedAnswerSimulation]) -> float:
        """% of supported claims that have a source URL (canonical citation capability)."""
        all_supported = [
            r for s in simulations
            for r in s.claim_decomposition
            if r.status in ("SUPPORTED", "PARTIALLY_SUPPORTED")
        ]
        if not all_supported:
            return 0.0
        with_url = sum(1 for r in all_supported if r.evidence_url)
        return round(with_url / len(all_supported) * 100, 1)
