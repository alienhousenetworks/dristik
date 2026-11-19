"""
Competitor Discovery Engine — Phase 7.1 (10/10 Transformation)

Identifies product-level and search competitors using 7 discrete vectors:
1. Business category overlap
2. Product category overlap
3. Search intent overlap
4. Search result (SERP) overlap
5. Geographic overlap
6. Commercial similarity
7. Customer audience overlap

STRICT GUARDRAIL:
No competitor is treated as part of the official benchmark group until
explicitly approved by the user. Rejections are permanently stored in the registry.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.competitive.models import (
    BenchmarkGroup,
    CompetitorApprovalStatus,
    CompetitorCandidate,
    DiscoveryVectorScore,
    DiscoveryVectorType,
)
from app.seo.competitive.resolution.domain_normalizer import (
    extract_brand_from_domain,
    is_valid_competitor_domain,
    normalize_domain,
)
from app.seo.competitive.resolution.rejection_store import CompetitorRejectionStore

logger = logging.getLogger("dristik.competitive.discovery")

VECTOR_WEIGHTS: Dict[DiscoveryVectorType, float] = {
    DiscoveryVectorType.BUSINESS_CATEGORY: 0.15,
    DiscoveryVectorType.PRODUCT_CATEGORY: 0.20,
    DiscoveryVectorType.SEARCH_INTENT: 0.20,
    DiscoveryVectorType.SEARCH_RESULT_SERP: 0.15,
    DiscoveryVectorType.GEOGRAPHIC: 0.10,
    DiscoveryVectorType.COMMERCIAL_SIMILARITY: 0.10,
    DiscoveryVectorType.CUSTOMER_AUDIENCE: 0.10,
}


class CompetitorDiscoveryEngine:
    def __init__(self, rejection_store: Optional[CompetitorRejectionStore] = None):
        self.rejection_store = rejection_store or CompetitorRejectionStore()

    def evaluate_7_vectors(
        self,
        target_domain: str,
        target_facts: Dict[str, Any],
        candidate_domain: str,
        candidate_facts: Dict[str, Any],
    ) -> Dict[str, DiscoveryVectorScore]:
        """Calculates explicit 0-100 scores for each of the 7 discovery vectors."""
        scores: Dict[str, DiscoveryVectorScore] = {}

        # 1. Business Category
        t_cat = (target_facts.get("business_category") or "").lower()
        c_cat = (candidate_facts.get("business_category") or "").lower()
        cat_overlap = 100.0 if t_cat and t_cat in c_cat or c_cat in t_cat else (50.0 if t_cat and c_cat else 20.0)
        scores[DiscoveryVectorType.BUSINESS_CATEGORY.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.BUSINESS_CATEGORY,
            score=cat_overlap,
            overlap_details=f"Target: '{t_cat}' vs Candidate: '{c_cat}'",
            rationale="Category taxonomy alignment."
        )

        # 2. Product Category
        t_prods = set(p.lower().strip() for p in target_facts.get("products", []))
        c_prods = set(p.lower().strip() for p in candidate_facts.get("products", []))
        prod_overlap_count = len(t_prods.intersection(c_prods))
        prod_score = min(100.0, (prod_overlap_count / max(1, len(t_prods))) * 100.0) if t_prods else 40.0
        scores[DiscoveryVectorType.PRODUCT_CATEGORY.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.PRODUCT_CATEGORY,
            score=round(prod_score, 1),
            overlap_details=f"Shared products: {list(t_prods.intersection(c_prods))}",
            rationale="Product catalog and service portfolio overlap."
        )

        # 3. Search Intent
        t_intent = set(i.lower().strip() for i in target_facts.get("search_intents", []))
        c_intent = set(i.lower().strip() for i in candidate_facts.get("search_intents", []))
        intent_overlap = len(t_intent.intersection(c_intent))
        intent_score = min(100.0, (intent_overlap / max(1, len(t_intent))) * 100.0) if t_intent else 50.0
        scores[DiscoveryVectorType.SEARCH_INTENT.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.SEARCH_INTENT,
            score=round(intent_score, 1),
            overlap_details=f"Shared query intents: {list(t_intent.intersection(c_intent))}",
            rationale="Buyer search journey and problem query overlap."
        )

        # 4. Search Result SERP Overlap
        serp_overlap_pct = float(candidate_facts.get("serp_overlap_pct", 0.0))
        scores[DiscoveryVectorType.SEARCH_RESULT_SERP.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.SEARCH_RESULT_SERP,
            score=min(100.0, max(0.0, serp_overlap_pct)),
            overlap_details=f"{serp_overlap_pct}% top-20 SERP co-occurrence",
            rationale="Observed organic Google search result co-ranking."
        )

        # 5. Geographic Overlap
        t_geo = (target_facts.get("geography") or "global").lower()
        c_geo = (candidate_facts.get("geography") or "global").lower()
        geo_score = 100.0 if t_geo == c_geo or "global" in (t_geo, c_geo) else 30.0
        scores[DiscoveryVectorType.GEOGRAPHIC.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.GEOGRAPHIC,
            score=geo_score,
            overlap_details=f"Target geo: '{t_geo}', Candidate geo: '{c_geo}'",
            rationale="Target market territory and delivery geography."
        )

        # 6. Commercial Similarity
        t_model = (target_facts.get("business_model") or "B2B").upper()
        c_model = (candidate_facts.get("business_model") or "B2B").upper()
        t_price = target_facts.get("pricing_model")
        c_price = candidate_facts.get("pricing_model")
        comm_score = 100.0 if t_model == c_model and t_price == c_price else (75.0 if t_model == c_model else 35.0)
        scores[DiscoveryVectorType.COMMERCIAL_SIMILARITY.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.COMMERCIAL_SIMILARITY,
            score=comm_score,
            overlap_details=f"Model: {t_model} vs {c_model}, Pricing: {t_price} vs {c_price}",
            rationale="Monetization model, sales motion, and pricing bracket comparability."
        )

        # 7. Customer Audience Overlap
        t_aud = set(a.lower().strip() for a in target_facts.get("target_audience", []))
        c_aud = set(a.lower().strip() for a in candidate_facts.get("target_audience", []))
        aud_overlap = len(t_aud.intersection(c_aud))
        aud_score = min(100.0, (aud_overlap / max(1, len(t_aud))) * 100.0) if t_aud else 50.0
        scores[DiscoveryVectorType.CUSTOMER_AUDIENCE.value] = DiscoveryVectorScore(
            vector=DiscoveryVectorType.CUSTOMER_AUDIENCE,
            score=round(aud_score, 1),
            overlap_details=f"Shared audience segments: {list(t_aud.intersection(c_aud))}",
            rationale="Target customer persona, company size, and user archetype match."
        )

        return scores

    def compute_composite_similarity(self, vector_scores: Dict[str, DiscoveryVectorScore]) -> float:
        total = 0.0
        for vec_type, weight in VECTOR_WEIGHTS.items():
            vec_res = vector_scores.get(vec_type.value)
            score_val = vec_res.score if vec_res else 0.0
            total += score_val * weight
        return round(total, 1)

    def discover_competitors(
        self,
        target_domain: str,
        target_facts: Dict[str, Any],
        raw_candidates: List[Dict[str, Any]],
        audit_run_id: str = "default_run",
    ) -> List[CompetitorCandidate]:
        clean_target = normalize_domain(target_domain)
        rejected_domains = set(self.rejection_store.get_rejected_domains(clean_target))

        candidates: List[CompetitorCandidate] = []
        for item in raw_candidates:
            c_domain = normalize_domain(item.get("domain", ""))
            if not is_valid_competitor_domain(c_domain, clean_target):
                continue

            vector_scores = self.evaluate_7_vectors(
                target_domain=clean_target,
                target_facts=target_facts,
                candidate_domain=c_domain,
                candidate_facts=item,
            )
            similarity = self.compute_composite_similarity(vector_scores)

            is_rejected = c_domain in rejected_domains
            status = CompetitorApprovalStatus.REJECTED if is_rejected else CompetitorApprovalStatus.DISCOVERED
            rejection_reason = "Previously rejected by user." if is_rejected else None

            candidate = CompetitorCandidate(
                domain=c_domain,
                company_name=item.get("company_name") or extract_brand_from_domain(c_domain),
                approval_status=status,
                similarity_score=similarity,
                vectors=vector_scores,
                rejection_reason=rejection_reason,
                provenance_id=f"prov_{audit_run_id}_{c_domain}",
            )
            candidates.append(candidate)

        # Sort descending by similarity
        candidates.sort(key=lambda c: c.similarity_score, reverse=True)
        return candidates

    def request_user_approval(
        self,
        candidates: List[CompetitorCandidate],
        top_k: int = 5,
        min_similarity: float = 40.0,
    ) -> List[CompetitorCandidate]:
        """Moves qualifying candidates into PENDING_USER_APPROVAL status."""
        qualifying = 0
        for c in candidates:
            if c.approval_status == CompetitorApprovalStatus.DISCOVERED:
                if c.similarity_score >= min_similarity and qualifying < top_k:
                    c.approval_status = CompetitorApprovalStatus.PENDING_USER_APPROVAL
                    qualifying += 1
        return candidates

    def approve_competitor(
        self,
        target_domain: str,
        candidate: CompetitorCandidate,
        approved_by: str = "user",
    ) -> CompetitorCandidate:
        candidate.approval_status = CompetitorApprovalStatus.APPROVED
        candidate.approved_at = datetime.now(timezone.utc)
        candidate.approved_by = approved_by
        candidate.rejection_reason = None
        return candidate

    def reject_competitor(
        self,
        target_domain: str,
        candidate: CompetitorCandidate,
        reason: str = "User rejected candidate",
    ) -> CompetitorCandidate:
        clean_target = normalize_domain(target_domain)
        clean_candidate = normalize_domain(candidate.domain)
        self.rejection_store.record_rejection(clean_target, clean_candidate)
        candidate.approval_status = CompetitorApprovalStatus.REJECTED
        candidate.rejection_reason = reason
        candidate.approved_at = None
        candidate.approved_by = None
        return candidate

    def build_official_benchmark_group(
        self,
        target_domain: str,
        candidates: List[CompetitorCandidate],
        approved_by: str = "user",
    ) -> BenchmarkGroup:
        """
        STRICT 10/10 RULE: Only competitors with status=APPROVED are permitted
        in the official benchmark group.
        """
        clean_target = normalize_domain(target_domain)
        approved_only = [c for c in candidates if c.approval_status == CompetitorApprovalStatus.APPROVED]
        return BenchmarkGroup(
            target_domain=clean_target,
            approved_competitors=approved_only,
            approved_by=approved_by,
            is_official=True,
        )


competitor_discovery_engine = CompetitorDiscoveryEngine()
