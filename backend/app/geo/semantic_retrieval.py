"""
Dristik AI GEO Controlled Semantic Retrieval Analysis.

Provides controlled semantic retrieval analysis of crawled website content using
Dristik's own deterministic chunking, embedding, and cosine similarity methodology.

IMPORTANT METHODOLOGY BOUNDARY:
These measurements represent Dristik's controlled semantic retrieval experiments.
They evaluate how well crawled website copy aligns semantically with buyer queries
under Dristik's configured embedding and chunking parameters.

They do NOT measure, predict, or reproduce the proprietary, undisclosed internal
retrieval pipelines, vector databases, or similarity thresholds of external AI
engines (such as ChatGPT, Perplexity, Gemini, Claude, or Google AI Overviews).
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.crawl.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalMethodology(BaseModel):
    """Explicit disclosure of Dristik's controlled retrieval configuration."""
    analyzer_name: str = "Dristik Controlled Semantic Retrieval Analysis"
    embedding_model: str = "intfloat/e5-small-v2"
    chunking_strategy: str = "fixed-sentence-window"
    chunk_size: int = 250
    chunk_overlap: int = 40
    similarity_metric: str = "cosine"
    similarity_threshold: float = 0.72
    methodology_version: str = "1.0"
    disclaimer: str = (
        "These measurements represent Dristik's controlled semantic retrieval methodology. "
        "They are not measurements or predictions of proprietary retrieval systems used by "
        "ChatGPT, Perplexity, Gemini, Claude, or other external AI engines."
    )


class RetrievalAnalysisConfig(BaseModel):
    """Configurable parameters for Dristik's controlled retrieval analysis."""
    chunk_size: int = Field(250, ge=50, le=800, description="Target chunk word count")
    chunk_overlap: int = Field(40, ge=0, le=200, description="Sliding sentence overlap words")
    similarity_threshold: float = Field(0.72, ge=0.0, le=1.0, description="Dristik retrieval qualification threshold")
    top_k: int = Field(3, ge=1, le=20, description="Number of top-ranked qualifying chunks")
    embedding_model: str = Field("intfloat/e5-small-v2", description="Configured embedding model")


class AnalyzedChunk(BaseModel):
    """A deterministic text chunk evaluated under Dristik's controlled retrieval methodology."""
    chunk_id: str
    source_url: str
    char_start: int
    char_end: int
    word_count: int
    content: str
    similarity_score: float = Field(
        ...,
        description="Cosine similarity between Dristik's query vector and this crawled text chunk."
    )
    passes_threshold: bool = Field(
        ...,
        description="True if similarity_score >= configured Dristik similarity_threshold."
    )
    retrieval_rank: Optional[int] = Field(
        None,
        description="Rank among qualifying chunks passing the Dristik threshold."
    )
    evaluation_notes: List[str] = Field(default_factory=list)
    evidence_type: str = "DERIVED"
    source_type: str = "CRAWLED_WEBSITE"
    methodology: str = "DRISTIK_CONTROLLED_SEMANTIC_RETRIEVAL"

    # Backward-compatibility property for prior SimulatedChunk callers
    @property
    def is_retrieved(self) -> bool:
        return self.passes_threshold

    @property
    def failure_reasons(self) -> List[str]:
        return self.evaluation_notes


class ControlledRetrievalReport(BaseModel):
    """Results of Dristik's controlled semantic retrieval analysis."""
    query_text: str
    source_url: str
    total_chunks: int
    qualifying_chunks_count: int
    top_chunk_similarity: float
    threshold_pass_rate_pct: float
    average_chunk_similarity: float
    methodology: RetrievalMethodology
    chunks: List[AnalyzedChunk] = Field(default_factory=list)
    content_structure_recommendations: List[str] = Field(default_factory=list)
    evidence_type: str = "DERIVED"
    source_type: str = "CRAWLED_WEBSITE"

    # Backward-compatibility properties
    @property
    def retrieved_chunks(self) -> int:
        return self.qualifying_chunks_count

    @property
    def retrieval_pass_rate_pct(self) -> float:
        return self.threshold_pass_rate_pct

    @property
    def dead_zone_recommendations(self) -> List[str]:
        return self.content_structure_recommendations

    @property
    def embedding_provider_used(self) -> str:
        return self.methodology.embedding_model


# Aliases for clean backward compatibility
SimulatedChunk = AnalyzedChunk
RagSimulationReport = ControlledRetrievalReport


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculates cosine similarity between two vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))


def _token_jaccard_similarity(query: str, text: str) -> float:
    """Deterministic lexical overlap similarity fallback when neural models are offline."""
    q_tokens = set(re.findall(r"\w+", query.lower()))
    t_tokens = set(re.findall(r"\w+", text.lower()))
    if not q_tokens or not t_tokens:
        return 0.0
    stopwords = {"what", "is", "the", "and", "for", "a", "an", "in", "on", "of", "to", "with", "our", "we"}
    q_sig = q_tokens - stopwords
    if not q_sig:
        q_sig = q_tokens
    intersection = q_sig.intersection(t_tokens)
    return round(len(intersection) / len(q_sig), 3)


class SemanticRetrievalAnalyzer:
    """
    Performs controlled semantic retrieval analysis over real crawled website content.
    Applies deterministic chunking and cosine similarity to evaluate semantic density.
    """

    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self._embedding_service = embedding_service

    def chunk_text(
        self,
        text: str,
        target_chunk_words: int = 250,
        overlap_words: int = 40
    ) -> List[Tuple[int, int, str]]:
        """
        Splits text into sliding chunks preserving sentence boundaries.
        Returns list of (char_start, char_end, chunk_text).
        """
        if not text or not text.strip():
            return []

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            words = text.split()
            return [(0, len(text), " ".join(words))]

        chunks: List[Tuple[int, int, str]] = []
        current_sentences: List[str] = []
        current_word_count = 0

        for sentence in sentences:
            s_words = sentence.split()
            s_len = len(s_words)

            if current_word_count + s_len > target_chunk_words and current_sentences:
                chunk_str = " ".join(current_sentences)
                start_idx = text.find(current_sentences[0]) if current_sentences else 0
                end_idx = start_idx + len(chunk_str)
                chunks.append((max(0, start_idx), end_idx, chunk_str))

                overlap_acc: List[str] = []
                overlap_len = 0
                for sent in reversed(current_sentences):
                    words_in_sent = len(sent.split())
                    if overlap_len + words_in_sent <= overlap_words:
                        overlap_acc.insert(0, sent)
                        overlap_len += words_in_sent
                    else:
                        break

                current_sentences = overlap_acc + [sentence]
                current_word_count = overlap_len + s_len
            else:
                current_sentences.append(sentence)
                current_word_count += s_len

        if current_sentences:
            chunk_str = " ".join(current_sentences)
            start_idx = text.find(current_sentences[0]) if current_sentences else 0
            end_idx = start_idx + len(chunk_str)
            chunks.append((max(0, start_idx), end_idx, chunk_str))

        return chunks

    def analyze_page_content(
        self,
        page_text: Optional[str],
        query: str,
        source_url: str = "https://target.domain/",
        config: Optional[RetrievalAnalysisConfig] = None,
        force_lexical: bool = False
    ) -> ControlledRetrievalReport:
        """
        Executes controlled semantic retrieval analysis for a given query over page content.
        Enforces zero-fake-data: does NOT invent chunks if page_text is empty or missing.
        """
        cfg = config or RetrievalAnalysisConfig()
        methodology = RetrievalMethodology(
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
            similarity_threshold=cfg.similarity_threshold,
            embedding_model=cfg.embedding_model,
        )

        # Zero-fake guard: no text means no chunks and no fabricated scores
        if not page_text or not page_text.strip():
            return ControlledRetrievalReport(
                query_text=query,
                source_url=source_url,
                total_chunks=0,
                qualifying_chunks_count=0,
                top_chunk_similarity=0.0,
                threshold_pass_rate_pct=0.0,
                average_chunk_similarity=0.0,
                methodology=methodology,
                chunks=[],
                content_structure_recommendations=["No crawled page content available to analyze."]
            )

        raw_chunks = self.chunk_text(
            page_text,
            target_chunk_words=cfg.chunk_size,
            overlap_words=cfg.chunk_overlap
        )
        if not raw_chunks:
            return ControlledRetrievalReport(
                query_text=query,
                source_url=source_url,
                total_chunks=0,
                qualifying_chunks_count=0,
                top_chunk_similarity=0.0,
                threshold_pass_rate_pct=0.0,
                average_chunk_similarity=0.0,
                methodology=methodology,
                chunks=[],
                content_structure_recommendations=["Page content contained no parseable sentences or words."]
            )

        provider_used = "lexical_jaccard"
        query_vec: List[float] = []
        doc_vecs: List[List[float]] = []

        if not force_lexical and self._embedding_service:
            try:
                if self._embedding_service.is_available():
                    query_vec = self._embedding_service.embed_query(query)
                    if query_vec:
                        chunk_texts = [c[2] for c in raw_chunks]
                        doc_vecs = self._embedding_service.embed_documents(chunk_texts)
                        if doc_vecs and len(doc_vecs) == len(raw_chunks):
                            provider_used = cfg.embedding_model
            except Exception as exc:
                logger.warning("[SemanticRetrievalAnalyzer] Neural embedding failed, using lexical overlap: %s", exc)

        methodology.embedding_model = provider_used

        scored_chunks: List[Dict[str, Any]] = []
        for i, (c_start, c_end, c_text) in enumerate(raw_chunks):
            words = len(c_text.split())
            if provider_used != "lexical_jaccard" and i < len(doc_vecs):
                sim = _cosine_similarity(query_vec, doc_vecs[i])
            else:
                sim = _token_jaccard_similarity(query, c_text)

            notes: List[str] = []
            if sim < cfg.similarity_threshold:
                notes.append(
                    f"Cosine similarity ({round(sim, 2)}) falls below Dristik's configured retrieval threshold ({cfg.similarity_threshold})"
                )
            if words < 40:
                notes.append("Short content chunk: low topical depth and limited extractable context")
            if not re.search(r"\d", c_text) and "pricing" in query.lower():
                notes.append("Passage contains no numerical pricing data or plan tiers")

            scored_chunks.append({
                "chunk_id": f"CHUNK-{i+1:02d}",
                "source_url": source_url,
                "char_start": c_start,
                "char_end": c_end,
                "word_count": words,
                "content": c_text,
                "similarity_score": round(sim, 3),
                "evaluation_notes": notes
            })

        # Rank chunks by similarity descending
        sorted_by_sim = sorted(enumerate(scored_chunks), key=lambda x: x[1]["similarity_score"], reverse=True)
        for rank, (orig_idx, _) in enumerate(sorted_by_sim, start=1):
            passes = (
                rank <= cfg.top_k
                and scored_chunks[orig_idx]["similarity_score"] >= cfg.similarity_threshold
            )
            scored_chunks[orig_idx]["passes_threshold"] = passes
            scored_chunks[orig_idx]["retrieval_rank"] = rank if passes else None

        result_chunks = [AnalyzedChunk(**sc) for sc in scored_chunks]
        qualifying_count = sum(1 for c in result_chunks if c.passes_threshold)
        top_sim = max([c.similarity_score for c in result_chunks], default=0.0)
        avg_sim = round(sum(c.similarity_score for c in result_chunks) / max(1, len(result_chunks)), 3)
        pass_rate = round((qualifying_count / max(1, len(result_chunks))) * 100, 1)

        recommendations: List[str] = []
        if qualifying_count == 0:
            recommendations.append(
                f"Low Semantic Similarity Region: No content chunks met Dristik's configured semantic retrieval threshold "
                f"({cfg.similarity_threshold}) for this query. Consider consolidating key answers into a focused, "
                "self-contained definition block."
            )
        elif top_sim < 0.80:
            recommendations.append(
                f"Moderate Semantic Similarity: Top chunk similarity ({top_sim}) meets Dristik's baseline threshold. "
                "Adding explicit entity definitions and factual specifications can improve semantic density."
            )
        else:
            recommendations.append(
                f"High Semantic Similarity: Chunk #{sorted_by_sim[0][1]['chunk_id']} exhibits strong semantic alignment "
                f"({top_sim}) with the query under Dristik's controlled methodology. "
                "Ensure surrounding JSON-LD structured data accurately reflects these claims."
            )

        return ControlledRetrievalReport(
            query_text=query,
            source_url=source_url,
            total_chunks=len(result_chunks),
            qualifying_chunks_count=qualifying_count,
            top_chunk_similarity=round(top_sim, 3),
            threshold_pass_rate_pct=pass_rate,
            average_chunk_similarity=avg_sim,
            methodology=methodology,
            chunks=result_chunks,
            content_structure_recommendations=recommendations,
        )

    # Backward-compatible method name matching previous interface
    def simulate_page_retrieval(
        self,
        page_text: Optional[str],
        query: str,
        source_url: str = "https://target.domain/",
        target_chunk_words: int = 250,
        similarity_threshold: float = 0.72,
        top_k: int = 3,
        force_lexical: bool = False
    ) -> ControlledRetrievalReport:
        cfg = RetrievalAnalysisConfig(
            chunk_size=target_chunk_words,
            similarity_threshold=similarity_threshold,
            top_k=top_k
        )
        return self.analyze_page_content(
            page_text=page_text,
            query=query,
            source_url=source_url,
            config=cfg,
            force_lexical=force_lexical
        )


# Backward-compatible alias
ControlledRetrievalAnalyzer = SemanticRetrievalAnalyzer
RagRetrievalSimulator = SemanticRetrievalAnalyzer

semantic_retrieval_analyzer = SemanticRetrievalAnalyzer()
controlled_retrieval_analyzer = semantic_retrieval_analyzer
rag_retrieval_simulator = semantic_retrieval_analyzer
