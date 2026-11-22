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

from app.crawl.knowledge.primitives import (
    AtomicClaim,
    KieClaimType,
    KieEvidenceStrength,
    PageRole,
)
from app.crawl.knowledge.website_knowledge_graph import WebsiteKnowledgeGraph


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
    __slots__ = ("claim", "bm25_score", "semantic_score", "dense_score", "page_role_boost",
                 "claim_type_boost", "lexical_signal_boost", "final_score")

    def __init__(self, claim: AtomicClaim):
        self.claim = claim
        self.bm25_score: float = 0.0
        self.semantic_score: float = 0.0
        self.dense_score: float = 0.0
        self.page_role_boost: float = 0.0
        self.claim_type_boost: float = 0.0
        self.lexical_signal_boost: float = 0.0
        self.final_score: float = 0.0


class HybridRetriever:
    """
    True Hybrid RAG Retriever (Dense VectorStore E5 + BM25 + Knowledge Graph + RRF).
    Combines:
      1. BM25 lexical scoring over Knowledge Graph claims & PageSection passages
      2. Dense vector cosine search via SQLite VectorStore (E5 embeddings) when available
      3. Jaccard token overlap semantic baseline
      4. Page role & claim type re-ranking + Reciprocal Rank Fusion (RRF)
    """

    TOP_K = 6

    def __init__(
        self,
        graph: WebsiteKnowledgeGraph,
        vector_store: Optional[Any] = None,
        embedding_service: Optional[Any] = None,
        domain: Optional[str] = None,
        analysis_id: Optional[str] = None,
        pages: Optional[List[Any]] = None,
    ):
        self.graph = graph
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.domain = (domain or getattr(graph, "domain", "") or "").replace("www.", "")
        self.analysis_id = analysis_id
        self._pages = list(pages or [])
        self._query_vec_cache: Dict[str, Optional[List[float]]] = {}

        # Combine Knowledge Graph claims + structured PageSection passages
        self._all_claims: List[AtomicClaim] = list(graph.claims or [])
        self._section_claims_added = 0
        if self._pages:
            self._append_page_section_claims()

        # Pre-compute per-claim token lists for BM25
        self._doc_tokens: Dict[str, List[str]] = {}
        for c in self._all_claims:
            doc_text = f"{c.predicate} {c.object} {c.evidence.exact_sentence if c.evidence else ''}"
            self._doc_tokens[c.claim_id] = _tokenize(doc_text)
        self._avg_doc_len = sum(len(t) for t in self._doc_tokens.values()) / max(1, len(self._doc_tokens))

    def _append_page_section_claims(self) -> None:
        """Index structured PageSections into the retrieval corpus so RAG sees full section text."""
        from app.crawl.knowledge.primitives import KieEvidence
        existing_snippets = {
            (c.evidence.url, (c.evidence.exact_sentence or "")[:120])
            for c in self._all_claims
            if c.evidence
        }
        for p in self._pages:
            p_url = getattr(p, "url", "") or ""
            p_role = self._page_role_for_url(p_url)
            for idx, sec in enumerate(getattr(p, "sections", None) or []):
                heading = (getattr(sec, "heading_text", None) or "").strip()
                body = (getattr(sec, "body_text", None) or "").strip()
                if len(body) < 30:
                    continue
                if (p_url, body[:120]) in existing_snippets:
                    continue
                sec_id = getattr(sec, "section_id", None) or f"sec_{idx}"
                cid = f"sec_claim_{abs(hash((p_url, sec_id))) % 10**9}"
                claim = AtomicClaim(
                    claim_id=cid,
                    subject=self.graph.brand,
                    predicate=heading or (getattr(sec, "section_role", None) or "section"),
                    object=body[:700],
                    claim_type=KieClaimType.FACT,
                    evidence=KieEvidence(
                        evidence_id=f"kie_{cid}",
                        url=p_url,
                        page_role=p_role,
                        section=heading or getattr(sec, "section_role", None) or "Section",
                        exact_sentence=body[:700],
                        strength=KieEvidenceStrength.HIGH,
                    ),
                )
                self._all_claims.append(claim)
                self._section_claims_added += 1

    def _page_role_for_url(self, url: str) -> PageRole:
        for pc in (getattr(self.graph, "page_classifications", None) or []):
            if pc.url == url:
                return getattr(pc, "page_role", PageRole.HOMEPAGE)
        low = (url or "").lower()
        if "/pricing" in low:
            return PageRole.PRICING
        if "/faq" in low:
            return PageRole.FAQ
        if "/about" in low:
            return PageRole.ABOUT
        if "/contact" in low:
            return PageRole.CONTACT
        if "/security" in low or "/privacy" in low:
            return PageRole.SECURITY
        if "/docs" in low or "/documentation" in low:
            return PageRole.DOCUMENTATION
        return PageRole.HOMEPAGE

    def _dense_search(self, question: str, top_k: int = 8) -> List[Dict[str, Any]]:
        """Query VectorStore with dense embeddings when available; fail silently to lexical."""
        if not self.vector_store or not self.embedding_service or not self.domain:
            return []
        try:
            # Skip embedding model initialization when no chunks are indexed for this domain
            if hasattr(self.vector_store, "count_chunks") and self.vector_store.count_chunks(self.domain) == 0:
                return []
            q_vec = self._query_vec_cache.get(question)
            if question not in self._query_vec_cache:
                if hasattr(self.embedding_service, "embed_query"):
                    q_vec = self.embedding_service.embed_query(question)
                elif hasattr(self.embedding_service, "embed_text"):
                    q_vec = self.embedding_service.embed_text(question)
                elif hasattr(self.embedding_service, "embed_batch"):
                    res = self.embedding_service.embed_batch([question])
                    q_vec = res[0] if res else None
                else:
                    q_vec = None
                self._query_vec_cache[question] = q_vec
            if not q_vec:
                return []
            return self.vector_store.search_similar(
                query_vector=q_vec,
                domain=self.domain,
                top_k=top_k,
                analysis_id=self.analysis_id,
            ) or []
        except Exception:
            return []

    def retrieve(self, question: str, plan: RetrievalPlan) -> List[RetrievedEvidenceChunk]:
        from app.crawl.knowledge.primitives import KieEvidence

        dense_hits = self._dense_search(question, top_k=8)
        if not self._all_claims and not dense_hits:
            return []

        query_tokens = _tokenize(question)
        brand_tokens = set(_tokenize(self.graph.brand))
        # Exclude brand name tokens so queries about "AlienHouse pricing" don't match every claim merely by company name
        topic_tokens = [t for t in query_tokens if t not in brand_tokens]
        if not topic_tokens:
            topic_tokens = query_tokens

        # Map dense hit scores by (url, prefix) and also synthesize chunks for dense-only passages
        dense_by_url_prefix: Dict[str, Tuple[int, float]] = {}
        dense_rank_by_url: Dict[str, Tuple[int, float]] = {}
        for rank_idx, hit in enumerate(dense_hits, start=1):
            h_url = str(hit.get("url") or "")
            h_text = str(hit.get("text") or hit.get("chunk_text") or "")
            h_score = float(hit.get("similarity") if hit.get("similarity") is not None else (hit.get("score") or 0.0))
            if h_score < 0.20:
                continue
            dense_by_url_prefix[f"{h_url}|{h_text[:80].lower()}"] = (rank_idx, h_score)
            if h_url not in dense_rank_by_url or h_score > dense_rank_by_url[h_url][1]:
                dense_rank_by_url[h_url] = (rank_idx, h_score)

        lexical_candidates: List[RetrievedEvidenceChunk] = []

        for claim in self._all_claims:
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

            # 2b. Dense vector similarity score from VectorStore if matched
            c_url = claim.evidence.url if claim.evidence else ""
            c_sent = (claim.evidence.exact_sentence if claim.evidence else "") or claim.object
            dense_match = dense_by_url_prefix.get(f"{c_url}|{c_sent[:80].lower()}") or dense_rank_by_url.get(c_url)
            if dense_match:
                chunk.dense_score = dense_match[1]

            # 3. Lexical signal boost (exact high-value tokens like $, soc, api)
            combined_lower = f"{claim.predicate} {claim.object}".lower()
            if plan.lexical_priority_signals:
                hits = sum(1 for s in plan.lexical_priority_signals if s in combined_lower)
                chunk.lexical_signal_boost = hits * 0.30

            # ── Relevance Gate ──────────────────────────────────────────
            # Boosts are re-rankers ONLY and must never promote an off-topic chunk.
            base_relevance = (
                (chunk.bm25_score * 0.45)
                + (chunk.semantic_score * 0.25)
                + (chunk.dense_score * 0.30)
                if chunk.dense_score > 0
                else (chunk.bm25_score * 0.60) + (chunk.semantic_score * 0.40)
            )
            has_topic_match = len(intersection) > 0
            has_lexical_signal = chunk.lexical_signal_boost > 0.0
            has_strong_dense = chunk.dense_score >= 0.45

            passes_relevance_gate = (
                (has_topic_match and base_relevance >= 0.10)
                or (has_lexical_signal and (has_topic_match or base_relevance >= 0.04))
                or has_strong_dense
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

            chunk.final_score = (
                base_relevance * 0.65
                + chunk.page_role_boost * 0.15
                + chunk.claim_type_boost * 0.10
                + min(0.30, chunk.lexical_signal_boost) * 0.10
            )
            if chunk.final_score >= 0.12 or has_strong_dense:
                lexical_candidates.append(chunk)

        # Promote high-scoring dense VectorStore passages not already represented in KG claims
        seen_prefixes = {
            (c.claim.evidence.url if c.claim.evidence else "", (c.claim.object or "")[:80].lower())
            for c in lexical_candidates
        }
        for rank_idx, hit in enumerate(dense_hits, start=1):
            h_score = float(hit.get("similarity") if hit.get("similarity") is not None else (hit.get("score") or 0.0))
            h_url = str(hit.get("url") or "")
            h_text = str(hit.get("text") or hit.get("chunk_text") or "").strip()
            if h_score < 0.35 or len(h_text) < 25:
                continue
            if (h_url, h_text[:80].lower()) in seen_prefixes:
                continue
            sec_heading = str(hit.get("section_heading") or hit.get("section_id") or "Section").strip()
            vec_cid = f"vec_{hit.get('id') or hit.get('chunk_id') or rank_idx}"
            dense_claim = AtomicClaim(
                claim_id=vec_cid,
                subject=self.graph.brand,
                predicate=sec_heading,
                object=h_text[:700],
                claim_type=KieClaimType.FACT,
                evidence=KieEvidence(
                    evidence_id=f"kie_{vec_cid}",
                    url=h_url,
                    page_role=self._page_role_for_url(h_url),
                    section=sec_heading,
                    exact_sentence=h_text[:700],
                    strength=KieEvidenceStrength.HIGH,
                ),
            )
            d_chunk = RetrievedEvidenceChunk(dense_claim)
            d_chunk.dense_score = h_score
            d_chunk.bm25_score = _bm25_score(topic_tokens, _tokenize(h_text), avg_len=self._avg_doc_len)
            d_chunk.final_score = round(h_score * 0.70 + d_chunk.bm25_score * 0.20, 4)
            lexical_candidates.append(d_chunk)
            seen_prefixes.add((h_url, h_text[:80].lower()))

        # Reciprocal Rank Fusion (RRF) combining lexical rank + dense rank
        if not lexical_candidates:
            return []
        by_lex = sorted(lexical_candidates, key=lambda c: (c.bm25_score + c.semantic_score), reverse=True)
        lex_rank = {c.claim.claim_id: i + 1 for i, c in enumerate(by_lex)}
        by_dense = sorted(lexical_candidates, key=lambda c: c.dense_score, reverse=True)
        dense_rank = {c.claim.claim_id: i + 1 for i, c in enumerate(by_dense) if c.dense_score > 0}

        k_rrf = 60.0
        for c in lexical_candidates:
            rrf = 1.0 / (k_rrf + lex_rank.get(c.claim.claim_id, 999))
            if c.claim.claim_id in dense_rank:
                rrf += 1.2 / (k_rrf + dense_rank[c.claim.claim_id])
            # Blend RRF rank signal with calibrated relevance score so threshold consumers stay consistent
            c.final_score = round(c.final_score * 0.75 + (rrf * 15.0) * 0.25, 4)

        lexical_candidates.sort(key=lambda c: c.final_score, reverse=True)
        return lexical_candidates[: self.TOP_K]
