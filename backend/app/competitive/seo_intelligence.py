"""
Competitive SEO Intelligence Engine — Phase 7.3 (10/10 Transformation)

Compares target domain vs approved competitors across 8 canonical vectors:
1. Keyword coverage
2. Search intent coverage
3. Page architecture
4. Content depth
5. Technical quality
6. Backlink profiles
7. Landing page coverage
8. Search visibility (where measurable; otherwise explicitly marked UNMEASURED)
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.competitive.models import (
    CompetitiveSeoComparison,
    CompetitorIngestionArtifact,
)
from app.seo.competitive.resolution.domain_normalizer import normalize_domain

logger = logging.getLogger("dristik.competitive.seo")


class CompetitiveSeoIntelligenceEngine:
    """
    Evaluates comparative SEO metrics between target and competitor sites.
    """

    def compare_seo(
        self,
        target_domain: str,
        target_artifact: CompetitorIngestionArtifact,
        competitor_artifact: CompetitorIngestionArtifact,
        target_keywords: Optional[List[str]] = None,
        competitor_keywords: Optional[List[str]] = None,
        authority_data: Optional[Dict[str, Any]] = None,
    ) -> CompetitiveSeoComparison:
        clean_target = normalize_domain(target_domain)
        clean_comp = normalize_domain(competitor_artifact.competitor_domain)

        t_pages = target_artifact.pages
        c_pages = competitor_artifact.pages

        # 1. Keyword Coverage
        t_kw_set = set(k.lower().strip() for k in (target_keywords or []))
        c_kw_set = set(k.lower().strip() for k in (competitor_keywords or []))
        shared_kw = t_kw_set.intersection(c_kw_set)
        comp_exclusive_kw = c_kw_set - t_kw_set
        kw_coverage = {
            "target_keywords_count": len(t_kw_set),
            "competitor_keywords_count": len(c_kw_set),
            "shared_keywords_count": len(shared_kw),
            "competitor_exclusive_keywords_count": len(comp_exclusive_kw),
            "competitor_exclusive_keywords_sample": sorted(list(comp_exclusive_kw))[:10],
            "keyword_overlap_ratio": round(len(shared_kw) / max(1, len(t_kw_set.union(c_kw_set))), 2),
        }

        # 2. Search Intent Coverage
        t_types = [p.page_type for p in t_pages]
        c_types = [p.page_type for p in c_pages]
        intent_coverage = {
            "target_intent_distribution": {
                "INFORMATIONAL": sum(1 for t in t_types if t in ["BLOG", "DOCS", "FAQ"]),
                "COMMERCIAL": sum(1 for t in t_types if t in ["PRODUCT", "CATEGORY"]),
                "TRANSACTIONAL": sum(1 for t in t_types if t in ["PRICING"]),
                "NAVIGATIONAL": sum(1 for t in t_types if t in ["HOMEPAGE", "ABOUT", "CONTACT"]),
            },
            "competitor_intent_distribution": {
                "INFORMATIONAL": sum(1 for t in c_types if t in ["BLOG", "DOCS", "FAQ"]),
                "COMMERCIAL": sum(1 for t in c_types if t in ["PRODUCT", "CATEGORY"]),
                "TRANSACTIONAL": sum(1 for t in c_types if t in ["PRICING"]),
                "NAVIGATIONAL": sum(1 for t in c_types if t in ["HOMEPAGE", "ABOUT", "CONTACT"]),
            },
        }

        # 3. Page Architecture
        page_architecture = {
            "target_total_pages": len(t_pages),
            "competitor_total_pages": len(c_pages),
            "target_page_types": list(set(t_types)),
            "competitor_page_types": list(set(c_types)),
            "architecture_gap": list(set(c_types) - set(t_types)),
        }

        # 4. Content Depth
        t_avg_words = round(sum(p.word_count for p in t_pages) / max(1, len(t_pages)), 1)
        c_avg_words = round(sum(p.word_count for p in c_pages) / max(1, len(c_pages)), 1)
        content_depth = {
            "target_avg_word_count": t_avg_words,
            "competitor_avg_word_count": c_avg_words,
            "depth_delta_words": round(t_avg_words - c_avg_words, 1),
            "content_leader": clean_target if t_avg_words >= c_avg_words else clean_comp,
        }

        # 5. Technical Quality
        t_avg_ttfb = round(sum(p.ttfb_ms or 200.0 for p in t_pages) / max(1, len(t_pages)), 1)
        c_avg_ttfb = round(sum(p.ttfb_ms or 200.0 for p in c_pages) / max(1, len(c_pages)), 1)
        t_schema_count = sum(len(p.structured_data_types) for p in t_pages)
        c_schema_count = sum(len(p.structured_data_types) for p in c_pages)
        technical_quality = {
            "target_avg_ttfb_ms": t_avg_ttfb,
            "competitor_avg_ttfb_ms": c_avg_ttfb,
            "target_total_schemas": t_schema_count,
            "competitor_total_schemas": c_schema_count,
            "technical_speed_winner": clean_target if t_avg_ttfb <= c_avg_ttfb else clean_comp,
        }

        # 6. Backlink Profiles
        auth = authority_data or {}
        t_backlinks = auth.get("target_referring_domains")
        c_backlinks = auth.get("competitor_referring_domains", {}).get(clean_comp)
        backlink_profiles = {
            "target_referring_domains": t_backlinks,
            "competitor_referring_domains": c_backlinks,
            "status": "AVAILABLE" if (t_backlinks is not None and c_backlinks is not None) else "UNMEASURED",
            "notes": "Backlink data provided via external authority connector." if t_backlinks else "No external authority connector attached; status=UNMEASURED."
        }

        # 7. Landing Page Coverage
        t_landing_count = sum(1 for p in t_pages if p.page_type in ["PRODUCT", "CATEGORY", "LANDING_PAGE"])
        c_landing_count = sum(1 for p in c_pages if p.page_type in ["PRODUCT", "CATEGORY", "LANDING_PAGE"])
        landing_page_coverage = {
            "target_commercial_landing_pages": t_landing_count,
            "competitor_commercial_landing_pages": c_landing_count,
            "coverage_delta": t_landing_count - c_landing_count,
        }

        # 8. Search Visibility
        t_vis = auth.get("target_visibility_score")
        c_vis = auth.get("competitor_visibility_scores", {}).get(clean_comp)
        search_visibility = {
            "target_visibility_score": t_vis,
            "competitor_visibility_score": c_vis,
            "status": "AVAILABLE" if (t_vis is not None and c_vis is not None) else "UNMEASURED",
            "notes": "SERP tracking data attached." if t_vis else "SERP visibility unmeasured; no simulated ranking ranks provided."
        }

        # Deterministic parity score calculation (0-100)
        score_points = 50
        if t_avg_words > c_avg_words:
            score_points += 15
        elif t_avg_words < c_avg_words:
            score_points -= 10

        if t_avg_ttfb < c_avg_ttfb:
            score_points += 15
        elif t_avg_ttfb > c_avg_ttfb:
            score_points -= 10

        if t_schema_count >= c_schema_count:
            score_points += 10
        else:
            score_points -= 5

        if len(shared_kw) > 0 and len(comp_exclusive_kw) == 0:
            score_points += 10

        parity_score = max(0, min(100, score_points))

        return CompetitiveSeoComparison(
            target_domain=clean_target,
            competitor_domain=clean_comp,
            keyword_coverage=kw_coverage,
            search_intent_coverage=intent_coverage,
            page_architecture=page_architecture,
            content_depth=content_depth,
            technical_quality=technical_quality,
            backlink_profiles=backlink_profiles,
            landing_page_coverage=landing_page_coverage,
            search_visibility=search_visibility,
            seo_parity_score=parity_score,
        )


competitive_seo_engine = CompetitiveSeoIntelligenceEngine()
