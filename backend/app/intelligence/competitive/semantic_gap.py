"""
Dristik AI Semantic Gap Engine
Leverages E5-Large embeddings and cosine similarity to evaluate:
1. Buyer Intent Coverage: How well the website's crawled chunks satisfy real buyer queries.
2. Competitor Semantic Gap: Missing topic clusters and coverage depth.
"""
import logging
from typing import List, Dict, Any, Optional
from app.crawl.embeddings import embedding_service
from app.crawl.vector_store import vector_store

logger = logging.getLogger("dristik.semantic_gap")


class SemanticGapEngine:
    def evaluate_intent_coverage(
        self,
        domain: str,
        queries: List[Dict[str, str]],
        min_similarity: float = 0.65,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates how semantically grounded the website's content is against buyer queries.
        Fails closed with explicit UNAVAILABLE status when neural embeddings are not available.
        """
        if not queries:
            return {"status": "NOT_EVALUATED", "coverage_score": None, "evaluations": []}

        if not embedding_service.is_available():
            return {
                "domain": domain,
                "status": "UNAVAILABLE",
                "overall_semantic_coverage_score": None,
                "total_queries_evaluated": len(queries),
                "evaluations": [],
                "reason": "Neural embedding model unconfigured or unreachable. Semantic intent coverage cannot be evaluated without live embeddings.",
                "missing_evidence_required": "Valid neural embedding model (SentenceTransformer or EMBEDDING_API_KEY)."
            }

        evaluations: List[Dict[str, Any]] = []
        scores: List[float] = []

        for q_obj in queries:
            query_text = q_obj.get("query", "")
            intent = q_obj.get("intent", "Commercial Search")
            
            q_vec = embedding_service.embed_query(query_text)
            if not q_vec:
                continue

            matches = vector_store.search_similar(
                query_vector=q_vec,
                domain=domain,
                top_k=3,
                min_score=min_similarity,
                analysis_id=analysis_id,
            )

            is_covered = len(matches) > 0
            best_sim = matches[0]["similarity"] if matches else 0.0
            best_chunk = matches[0]["text"][:240] + "..." if matches else "No matching semantic coverage found on crawled pages."
            best_url = matches[0]["url"] if matches else None

            scores.append(best_sim)
            evaluations.append({
                "query": query_text,
                "intent": intent,
                "is_covered": is_covered,
                "semantic_similarity": best_sim,
                "best_matching_url": best_url,
                "evidence_snippet": best_chunk
            })

        avg_sim = sum(scores) / len(scores) if scores else None
        coverage_score = int(round(avg_sim * 100)) if avg_sim is not None else None

        return {
            "domain": domain,
            "status": "AVAILABLE" if coverage_score is not None else "INSUFFICIENT_EVIDENCE",
            "overall_semantic_coverage_score": coverage_score,
            "total_queries_evaluated": len(queries),
            "evaluations": evaluations
        }


semantic_gap_engine = SemanticGapEngine()
