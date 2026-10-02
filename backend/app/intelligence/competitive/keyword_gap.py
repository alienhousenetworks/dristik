"""
Dristik Competitor Keyword Gap Engine
Calculates commercial keyword gaps between target domain and competitors.
Identifies:
1. Missing Keywords (competitor ranks top 10, target does not rank)
2. Weak Keywords (target ranks on page 2-3, competitor ranks top 5)
3. Traffic Opportunity Estimation (Volume * CTR model)
4. Actionable landing page creation recommendations
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.domain.models import KeywordGapItem, KeywordGapReport
from app.external_authority.store import ExternalStore

logger = logging.getLogger("dristik.keyword_gap")

_CTR_BY_POSITION = {
    1: 0.28,
    2: 0.15,
    3: 0.11,
    4: 0.07,
    5: 0.06,
    6: 0.04,
    7: 0.03,
    8: 0.03,
    9: 0.02,
    10: 0.02,
}


def _clean_domain(domain_or_url: str) -> str:
    raw = (domain_or_url or "").strip().lower()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    return parsed.netloc.replace("www.", "").split(":")[0]


def _slugify(text: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return f"/{clean}"


def _estimate_opportunity(volume: int, comp_rank: int) -> int:
    ctr = _CTR_BY_POSITION.get(comp_rank, 0.01 if comp_rank <= 20 else 0.005)
    return int(round(volume * ctr))


class KeywordGapEngine:
    def __init__(self, store: Optional[ExternalStore] = None):
        self.store = store or ExternalStore()

    def evaluate_gap(
        self,
        target_domain: str,
        competitor_domains: List[str],
        project_id: Optional[str] = None,
    ) -> KeywordGapReport:
        clean_target = _clean_domain(target_domain)
        clean_comps = [_clean_domain(c) for c in competitor_domains if c and _clean_domain(c) != clean_target]

        opportunities: List[KeywordGapItem] = []

        # 1. First check if we have tracked project keywords with competitor rankings
        if project_id:
            db_opps = self._evaluate_from_project_store(project_id, clean_target, clean_comps)
            opportunities.extend(db_opps)

        # 2. Check if live DataForSEO domain intersection can be queried
        has_dataforseo = bool(
            (settings.DATAFORSEO_LOGIN or "") and (settings.DATAFORSEO_PASSWORD or "")
        )
        if has_dataforseo and clean_comps:
            live_opps = self._query_dataforseo_domain_intersection(clean_target, clean_comps[0])
            for item in live_opps:
                if not any(o.keyword.lower() == item.keyword.lower() for o in opportunities):
                    opportunities.append(item)

        # Sort opportunities by estimated monthly traffic potential descending
        opportunities.sort(key=lambda o: o.estimated_monthly_visits_opportunity, reverse=True)

        missing_count = sum(1 for o in opportunities if o.gap_type == "MISSING_OPPORTUNITY")
        weak_count = sum(1 for o in opportunities if o.gap_type == "WEAK_PAGE_2")
        total_traffic = sum(o.estimated_monthly_visits_opportunity for o in opportunities)

        if opportunities:
            summary = (
                f"Identified {len(opportunities)} commercial keyword gap opportunities against "
                f"{', '.join(clean_comps[:2])}. Closing these gaps represents an estimated "
                f"+{total_traffic:,} monthly organic search visits."
            )
        else:
            summary = (
                f"No competitor keyword gaps recorded yet for {clean_target}. Add tracked keywords or connect "
                f"DataForSEO to perform automated cross-domain search intersection."
            )

        return KeywordGapReport(
            target_domain=clean_target,
            competitor_domains=clean_comps,
            total_missing_keywords=missing_count,
            total_weak_keywords=weak_count,
            total_opportunity_traffic=total_traffic,
            opportunities=opportunities[:50],  # Return top 50 prioritized opportunities
            summary=summary,
        )

    def _evaluate_from_project_store(
        self,
        project_id: str,
        target_domain: str,
        competitors: List[str],
    ) -> List[KeywordGapItem]:
        items: List[KeywordGapItem] = []
        tracked = self.store.list_project_keywords(project_id, active_only=True)

        for kw in tracked:
            kw_id = kw["keyword_id"]
            kw_text = kw["keyword"]
            volume = int(kw.get("search_volume") or 0)
            target_pos = kw.get("current_position")
            kd = kw.get("keyword_difficulty")
            cpc = float(kw.get("cpc_usd") or 0.0)

            comp_ranks = self.store.get_keyword_competitors(kw_id)
            for cr in comp_ranks:
                comp_dom = cr.get("competitor_domain", "")
                c_pos = cr.get("position")
                if not c_pos:
                    continue

                slug = _slugify(kw_text)

                # Case 1: Competitor ranks in top 10, Target is unranked
                if c_pos <= 10 and (target_pos is None or target_pos > 100):
                    opp_traffic = _estimate_opportunity(volume, c_pos)
                    items.append(KeywordGapItem(
                        keyword=kw_text,
                        search_volume=volume,
                        keyword_difficulty=kd,
                        cpc_usd=cpc,
                        competitor_domain=comp_dom,
                        competitor_rank=c_pos,
                        target_rank=None,
                        gap_type="MISSING_OPPORTUNITY",
                        estimated_monthly_visits_opportunity=opp_traffic,
                        recommended_action=f"Create dedicated landing page: {slug} to capture '{kw_text}'",
                        recommended_page_slug=slug,
                    ))

                # Case 2: Competitor ranks in top 5, Target ranks on page 2-3 (11-30)
                elif c_pos <= 5 and target_pos and 11 <= target_pos <= 30:
                    opp_traffic = _estimate_opportunity(volume, c_pos)
                    items.append(KeywordGapItem(
                        keyword=kw_text,
                        search_volume=volume,
                        keyword_difficulty=kd,
                        cpc_usd=cpc,
                        competitor_domain=comp_dom,
                        competitor_rank=c_pos,
                        target_rank=target_pos,
                        gap_type="WEAK_PAGE_2",
                        estimated_monthly_visits_opportunity=opp_traffic,
                        recommended_action=f"Optimize existing page {kw.get('target_url') or slug} with richer schema and entity depth to jump from #{target_pos} to top 5",
                        recommended_page_slug=kw.get("target_url") or slug,
                    ))

        return items

    def _query_dataforseo_domain_intersection(
        self,
        target_domain: str,
        competitor_domain: str,
    ) -> List[KeywordGapItem]:
        import httpx
        items: List[KeywordGapItem] = []
        try:
            payload = [{
                "target1": competitor_domain,
                "target2": target_domain,
                "location_code": 2840,
                "language_code": "en",
                "intersections": [1],  # Keywords where target1 ranks but target2 doesn't
                "limit": 30,
                "order_by": ["1.keyword_data.keyword_info.search_volume,desc"],
            }]
            res = httpx.post(
                "https://api.dataforseo.com/v3/dataforseo_labs/google/domain_intersection/live",
                json=payload,
                auth=(settings.DATAFORSEO_LOGIN or "", settings.DATAFORSEO_PASSWORD or ""),
                timeout=20.0,
            )
            if res.status_code != 200:
                return []
            data = res.json()
            tasks = data.get("tasks") or []
            if not tasks or not tasks[0].get("result"):
                return []
            results = tasks[0]["result"]
            for row in results:
                kw_data = row.get("keyword_data") or {}
                kw_text = kw_data.get("keyword")
                if not kw_text:
                    continue
                info = kw_data.get("keyword_info") or {}
                vol = int(info.get("search_volume") or 0)
                cpc = float(info.get("cpc") or 0.0)
                kd = kw_data.get("keyword_properties", {}).get("keyword_difficulty")

                first_domain_data = row.get("first_domain_serp_element") or {}
                comp_rank = int(first_domain_data.get("rank_group") or 10)

                slug = _slugify(kw_text)
                traffic = _estimate_opportunity(vol, comp_rank)

                items.append(KeywordGapItem(
                    keyword=kw_text,
                    search_volume=vol,
                    keyword_difficulty=kd,
                    cpc_usd=cpc,
                    competitor_domain=competitor_domain,
                    competitor_rank=comp_rank,
                    target_rank=None,
                    gap_type="MISSING_OPPORTUNITY",
                    estimated_monthly_visits_opportunity=traffic,
                    recommended_action=f"Create dedicated landing page: {slug} to target '{kw_text}' (competitor ranks #{comp_rank})",
                    recommended_page_slug=slug,
                ))
        except Exception as exc:
            logger.warning("DataForSEO domain intersection query failed: %s", exc)
        return items


keyword_gap_engine = KeywordGapEngine()
