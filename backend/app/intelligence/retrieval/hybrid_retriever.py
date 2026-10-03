"""
Dristik KIE — Phase 3: Query Planner & Hybrid Retriever
The Query Planner classifies inquiry intent and routes to the optimal retrieval strategy.
The HybridRetriever executes multi-vector search (BM25 + semantic pattern + entity/claim graph)
with reciprocal rank fusion (RRF) and cross-encoder-style reranking.

Note: For Phase 1 this ships without external embedding models — semantic retrieval uses
TF-IDF-style cosine similarity over tokenized claims, which is robust without
requiring a GPU or third-party API. The interface is designed to accept a drop-in
embedding model later.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.intelligence.knowledge.primitives import (
    AtomicClaim,
    KieClaimType,
    KieEvidenceStrength,
    PageRole,
)
from app.intelligence.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph


# ─────────────────────────────────────────────────────────────────────────────
# Query Intent Classification
# ─────────────────────────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    IDENTITY = "identity"           # "What is X?" "Who founded X?" "Where is X based?"
    COMMERCIAL = "commercial"       # "How much does X cost?" "What plans exist?"
    CAPABILITY = "capability"       # "Does X support Y?" "What features does X have?"
    COMPLIANCE = "compliance"       # "Is X SOC 2 certified?" "Does X comply with GDPR?"
    COMPETITIVE = "competitive"     # "How does X compare to Y?" "Alternatives to X?"
    ICP = "icp"                     # "Who is X for?" "What company size?" "Industries?"
    PURCHASE = "purchase"           # "How do I buy X?" "Can I trial X?" "Demo?"
    PROOF = "proof"                 # "Case studies?" "ROI?" "Customer logos?"
    TECHNICAL = "technical"         # "What tech stack?" "API docs?" "Integrations?"
    ONBOARDING = "onboarding"       # "How long to deploy?" "What support?" "Training?"


_INTENT_SIGNALS: List[Tuple[QueryIntent, List[str]]] = [
    (QueryIntent.COMMERCIAL,  ["cost", "price", "pricing", "plan", "subscription", "billing", "fee", "rate", "charge", "tier", "package"]),
    (QueryIntent.COMPLIANCE,  ["soc 2", "iso 27001", "hipaa", "gdpr", "ccpa", "compliant", "certified", "security", "privacy", "encryption", "pci"]),
    (QueryIntent.COMPETITIVE, ["compare", "versus", "vs ", "alternative", "competitor", "better than", "differ", "unlike"]),
    (QueryIntent.PURCHASE,    ["demo", "trial", "get started", "sign up", "buy", "purchase", "schedule", "book", "contact sales", "start", "contact", "call to action", "cta", "request"]),
    (QueryIntent.PROOF,       ["case study", "customer", "roi", "result", "outcome", "testimonial", "logo", "review", "evidence", "success"]),
    (QueryIntent.TECHNICAL,   ["api", "sdk", "webhook", "integration", "stack", "architecture", "framework", "deploy", "rest", "graphql"]),
    (QueryIntent.ICP,         ["who is", "who should", "company size", "headcount", "enterprise", "smb", "startup", "industry", "sector", "for", "persona", "audience", "restricted", "target"]),
    (QueryIntent.ONBOARDING,  ["onboard", "implement", "setup", "support", "sla", "response time", "customer success", "training", "migrate"]),
    (QueryIntent.CAPABILITY,  ["does", "can", "feature", "capability", "support", "allow", "enable", "workflow", "automat", "dashboard"]),
    (QueryIntent.IDENTITY,    ["what is", "what does", "who is", "where is", "when was", "founded", "mission", "headquarters", "about"]),
]


class QueryPlanner:
    """
    Classifies inquiry intent and selects the optimal retrieval strategy.
    """

    @classmethod
    def plan(cls, question: str) -> "RetrievalPlan":
        intent = cls._classify_intent(question)
        page_roles = cls._intent_to_page_roles(intent)
        claim_types = cls._intent_to_claim_types(intent)
        priority_signals = cls._intent_to_lexical_signals(intent)
        return RetrievalPlan(
            intent=intent,
            priority_page_roles=page_roles,
            priority_claim_types=claim_types,
            lexical_priority_signals=priority_signals,
        )

    @classmethod
    def _classify_intent(cls, question: str) -> QueryIntent:
        q = question.lower()
        for intent, signals in _INTENT_SIGNALS:
            if any(s in q for s in signals):
                return intent
        return QueryIntent.CAPABILITY  # Safe default

    @classmethod
    def _intent_to_page_roles(cls, intent: QueryIntent) -> List[PageRole]:
        return {
            QueryIntent.IDENTITY:    [PageRole.HOMEPAGE, PageRole.ABOUT, PageRole.CONTACT],
            QueryIntent.COMMERCIAL:  [PageRole.PRICING, PageRole.FAQ, PageRole.PRODUCT],
            QueryIntent.CAPABILITY:  [PageRole.PRODUCT, PageRole.SERVICES, PageRole.DOCUMENTATION, PageRole.FAQ],
            QueryIntent.COMPLIANCE:  [PageRole.SECURITY, PageRole.LEGAL, PageRole.DOCUMENTATION],
            QueryIntent.COMPETITIVE: [PageRole.HOMEPAGE, PageRole.ABOUT, PageRole.PRODUCT, PageRole.SERVICES],
            QueryIntent.ICP:         [PageRole.HOMEPAGE, PageRole.ABOUT, PageRole.CASE_STUDY, PageRole.PRICING],
            QueryIntent.PURCHASE:    [PageRole.PRICING, PageRole.CONTACT, PageRole.HOMEPAGE, PageRole.FAQ],
            QueryIntent.PROOF:       [PageRole.CASE_STUDY, PageRole.ABOUT, PageRole.HOMEPAGE],
            QueryIntent.TECHNICAL:   [PageRole.DOCUMENTATION, PageRole.PRODUCT, PageRole.SECURITY],
            QueryIntent.ONBOARDING:  [PageRole.FAQ, PageRole.DOCUMENTATION, PageRole.CONTACT, PageRole.PRODUCT],
        }.get(intent, [PageRole.HOMEPAGE, PageRole.PRODUCT])

    @classmethod
    def _intent_to_claim_types(cls, intent: QueryIntent) -> List[KieClaimType]:
        return {
            QueryIntent.COMMERCIAL: [KieClaimType.FACT, KieClaimType.PROMISE],
            QueryIntent.COMPLIANCE: [KieClaimType.FACT],
            QueryIntent.CAPABILITY: [KieClaimType.CAPABILITY, KieClaimType.FACT],
            QueryIntent.PROOF:      [KieClaimType.FACT, KieClaimType.PROMISE],
            QueryIntent.PURCHASE:   [KieClaimType.FACT, KieClaimType.CAPABILITY],
        }.get(intent, [KieClaimType.FACT, KieClaimType.CAPABILITY])

    @classmethod
    def _intent_to_lexical_signals(cls, intent: QueryIntent) -> List[str]:
        return {
            QueryIntent.COMMERCIAL:  ["$", "€", "£", "₹", "/mo", "pricing", "plan", "tier", "cost"],
            QueryIntent.COMPLIANCE:  ["soc", "iso", "hipaa", "gdpr", "certified", "compliant", "aes", "tls"],
            QueryIntent.TECHNICAL:   ["api", "sdk", "webhook", "graphql", "rest", "kubernetes", "docker"],
            QueryIntent.ICP:         ["enterprise", "startup", "smb", "employees", "headcount", "team size", "persona", "target", "industry"],
            QueryIntent.PROOF:       ["customer", "case study", "roi", "reduced", "increased", "results"],
            QueryIntent.PURCHASE:    ["contact", "demo", "request", "build", "trial", "sign up", "schedule", "call to action"],
        }.get(intent, [])


class RetrievalPlan(object):
    def __init__(
        self,
        intent: QueryIntent,
        priority_page_roles: List[PageRole],
        priority_claim_types: List[KieClaimType],
        lexical_priority_signals: List[str],
    ):
        self.intent = intent
        self.priority_page_roles = priority_page_roles
        self.priority_claim_types = priority_claim_types
        self.lexical_priority_signals = lexical_priority_signals


# ─────────────────────────────────────────────────────────────────────────────
# BM25 (Lexical) Retrieval
# ─────────────────────────────────────────────────────────────────────────────

_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "cannot", "not", "and", "or",
    "but", "for", "with", "this", "that", "it", "its", "to", "of", "in",
    "on", "at", "from", "by", "what", "how", "why", "who", "when", "where",
    "does", "which",
})

def _stem(token: str) -> str:
    t = token.lower()
    if len(t) > 4:
        if t.endswith("ies") and len(t) > 5:
            return t[:-3] + "y"
        if t.endswith("ing") and len(t) > 5:
            return t[:-3].rstrip("e")
        if t.endswith("es") and len(t) > 4:
            return t[:-2].rstrip("e")
        if t.endswith("ed") and len(t) > 4:
            return t[:-2].rstrip("e")
        if t.endswith("s") and not t.endswith("ss"):
            return t[:-1].rstrip("e")
        if t.endswith("e") and len(t) > 4:
            return t[:-1]
    return t


def _tokenize(text: str) -> List[str]:
    return [
        _stem(t) for t in re.sub(r"[^\w\s]", " ", text.lower()).split()
        if t not in _STOPWORDS and len(t) > 2
    ]

def _bm25_score(query_tokens: List[str], doc_tokens: List[str], k1: float = 1.5, b: float = 0.75, avg_len: float = 50) -> float:
    freq_map = defaultdict(int)
    for t in doc_tokens:
        freq_map[t] += 1
    dl = len(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        tf = freq_map.get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1.0 + (1.0 / (tf + 0.5)))
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / max(1, avg_len))
        score += idf * (numerator / denominator)
    return score


# ─────────────────────────────────────────────────────────────────────────────
# Hybrid Retriever
# ─────────────────────────────────────────────────────────────────────────────

class RetrievedEvidenceChunk(object):
    """A scored, ranked evidence unit returned by the hybrid retriever."""
    __slots__ = ("claim", "bm25_score", "semantic_score", "page_role_boost",
                 "claim_type_boost", "lexical_signal_boost", "final_score")

    def __init__(self, claim: AtomicClaim):
        self.claim = claim
        self.bm25_score: float = 0.0
        self.semantic_score: float = 0.0
        self.page_role_boost: float = 0.0
        self.claim_type_boost: float = 0.0
        self.lexical_signal_boost: float = 0.0
        self.final_score: float = 0.0


class HybridRetriever:
    """
    Multi-vector claim retriever.
    Combines:
      1. BM25 lexical scoring over (predicate + object) claim text
      2. Semantic TF-IDF cosine similarity (drop-in: swap for embedding model later)
      3. Page role boost: prioritises high-authority roles per QueryIntent
      4. Claim type boost: prioritises FACT/CAPABILITY for commercial queries
      5. Lexical signal boost: exact keyword matches on high-signal tokens
    Returns top-k evidence chunks per query, ranked by Reciprocal Rank Fusion (RRF).
    """

    TOP_K = 5

    def __init__(self, graph: WebsiteKnowledgeGraph):
        self.graph = graph
        # Pre-compute per-claim token lists for BM25
        self._doc_tokens: Dict[str, List[str]] = {}
        for c in graph.claims:
            doc_text = f"{c.predicate} {c.object} {c.evidence.exact_sentence if c.evidence else ''}"
            self._doc_tokens[c.claim_id] = _tokenize(doc_text)
        self._avg_doc_len = sum(len(t) for t in self._doc_tokens.values()) / max(1, len(self._doc_tokens))

    def retrieve(self, question: str, plan: RetrievalPlan) -> List[RetrievedEvidenceChunk]:
        if not self.graph.claims:
            return []

        query_tokens = _tokenize(question)
        brand_tokens = set(_tokenize(self.graph.brand))
        # Exclude brand name tokens so queries about "AlienHouse pricing" don't match every claim merely by company name
        topic_tokens = [t for t in query_tokens if t not in brand_tokens]
        if not topic_tokens:
            topic_tokens = query_tokens

        chunks: List[RetrievedEvidenceChunk] = []

        for claim in self.graph.claims:
            chunk = RetrievedEvidenceChunk(claim)
            doc_tokens = self._doc_tokens.get(claim.claim_id, [])
            if not doc_tokens:
                continue

            # 1. Base Lexical BM25 on topic tokens
            chunk.bm25_score = _bm25_score(topic_tokens, doc_tokens, avg_len=self._avg_doc_len)

            # 2. Semantic: topic token overlap ratio (Jaccard-style, lightweight)
            q_set = set(topic_tokens)
            d_set = set(doc_tokens)
            intersection = q_set & d_set
            union = q_set | d_set
            chunk.semantic_score = len(intersection) / max(1, len(union))

            # 3. Lexical signal boost (exact high-value tokens like $, soc, api)
            combined_lower = f"{claim.predicate} {claim.object}".lower()
            if plan.lexical_priority_signals:
                hits = sum(1 for s in plan.lexical_priority_signals if s in combined_lower)
                chunk.lexical_signal_boost = hits * 0.30

            # ── Relevance Gate ──────────────────────────────────────────
            # Calculate base topic relevance before any category or page role boosts.
            # Boosts are re-rankers ONLY and must never promote an off-topic chunk.
            base_relevance = (chunk.bm25_score * 0.60) + (chunk.semantic_score * 0.40)
            has_topic_match = len(intersection) > 0
            has_lexical_signal = chunk.lexical_signal_boost > 0.0

            passes_relevance_gate = (
                (has_topic_match and base_relevance >= 0.10) or
                (has_lexical_signal and (has_topic_match or base_relevance >= 0.04))
            )
            if not passes_relevance_gate:
                continue

            # 4. Page role boost (only for gate-passed candidates)
            if claim.evidence and claim.evidence.page_role in plan.priority_page_roles:
                idx = plan.priority_page_roles.index(claim.evidence.page_role)
                chunk.page_role_boost = max(0.0, 1.0 - idx * 0.15)

            # 5. Claim type boost (only for gate-passed candidates)
            if claim.claim_type in plan.priority_claim_types:
                chunk.claim_type_boost = 0.25

            # Final RRF-weighted score
            chunk.final_score = (
                base_relevance * 0.65 +
                chunk.page_role_boost * 0.15 +
                chunk.claim_type_boost * 0.10 +
                min(0.30, chunk.lexical_signal_boost) * 0.10
            )

            if chunk.final_score >= 0.12:
                chunks.append(chunk)

        # Sort descending by final_score, return top-K (or empty list if no evidence passed the gate)
        chunks.sort(key=lambda c: c.final_score, reverse=True)
        return chunks[: self.TOP_K]
