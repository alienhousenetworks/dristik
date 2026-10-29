"""
Dristik Continuous Keyword Tracking & SERP History Engine
Tracks daily rank movements, SERP features (AI Overviews, Featured Snippets, Local Pack),
and competitor rank positions across target keywords.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.core.config import settings
from app.domain.models import (
    KeywordMovementSummary,
    KeywordSerpSnapshot,
    TrackedKeyword,
)
from app.connectors.authority.store import ExternalStore, default_db_path

logger = logging.getLogger("dristik.serp_tracker")


def _clean_domain(domain_or_url: str) -> str:
    raw = (domain_or_url or "").strip().lower()
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    return parsed.netloc.replace("www.", "").split(":")[0]


class SerpTrackingEngine:
    def __init__(self, store: Optional[ExternalStore] = None):
        self.store = store or ExternalStore()

    def add_keyword(
        self,
        project_id: str,
        domain: str,
        keyword: str,
        target_url: Optional[str] = None,
        intent: str = "Commercial",
        tags: Optional[List[str]] = None,
        search_volume: int = 0,
        cpc_usd: float = 0.0,
        keyword_difficulty: Optional[int] = None,
    ) -> TrackedKeyword:
        domain = _clean_domain(domain)
        kw_clean = keyword.strip()
        kw_id = self.store.upsert_project_keyword({
            "project_id": project_id,
            "domain": domain,
            "keyword": kw_clean,
            "target_url": target_url,
            "intent": intent or "Commercial",
            "tags": tags or [],
            "search_volume": search_volume,
            "cpc_usd": cpc_usd,
            "keyword_difficulty": keyword_difficulty,
        })
        row = self.store.get_project_keyword(kw_id)
        if not row:
            raise RuntimeError(f"Failed to retrieve created keyword {kw_id}")
        return TrackedKeyword(**row)

    def list_keywords(self, project_id: str, active_only: bool = True) -> List[TrackedKeyword]:
        rows = self.store.list_project_keywords(project_id, active_only=active_only)
        return [TrackedKeyword(**r) for r in rows]

    def remove_keyword(self, project_id: str, keyword_id: str) -> bool:
        return self.store.delete_project_keyword(project_id, keyword_id)

    def get_history(self, keyword_id: str, days: int = 30) -> List[KeywordSerpSnapshot]:
        rows = self.store.get_keyword_serp_history(keyword_id, limit=days)
        return [KeywordSerpSnapshot(**r) for r in rows]

    def get_competitor_ranks(self, keyword_id: str, snapshot_date: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.store.get_keyword_competitors(keyword_id, snapshot_date=snapshot_date)

    def sync_keyword_serp(
        self,
        project_id: str,
        domain: str,
        competitor_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Polls live SERP data for all active keywords of a project.
        Parses target rank, SERP features (AI Overview, Snippet, PAA),
        and rival ranks. Stores daily snapshots.
        """
        clean_target = _clean_domain(domain)
        competitors = [_clean_domain(c) for c in (competitor_domains or []) if c]
        keywords = self.store.list_project_keywords(project_id, active_only=True)
        today = datetime.now(timezone.utc).date().isoformat()

        if not keywords:
            return {
                "synced_count": 0,
                "date": today,
                "message": "No active keywords tracked for this project.",
            }

        # Check if live DataForSEO or SerpAPI credentials are configured
        has_dataforseo = bool(
            (settings.DATAFORSEO_LOGIN or "") and (settings.DATAFORSEO_PASSWORD or "")
        )
        has_serpapi = bool(settings.SERPAPI_KEY)

        synced_count = 0
        updated_keywords: List[TrackedKeyword] = []

        for kw in keywords:
            kw_id = kw["keyword_id"]
            kw_text = kw["keyword"]
            prev_pos = kw.get("current_position")

            position: Optional[int] = None
            ranking_url: Optional[str] = None
            serp_features: List[str] = []
            has_ai_overview = False
            has_snippet = False
            has_local = False
            comp_records: List[Dict[str, Any]] = []

            if has_dataforseo:
                pos_info = self._query_dataforseo_serp(kw_text, clean_target, competitors)
                if pos_info:
                    position = pos_info.get("target_position")
                    ranking_url = pos_info.get("target_url")
                    serp_features = pos_info.get("features", [])
                    has_ai_overview = "ai_overview" in serp_features
                    has_snippet = "featured_snippet" in serp_features
                    has_local = "local_pack" in serp_features
                    comp_records = pos_info.get("competitors", [])
            elif has_serpapi:
                pos_info = self._query_serpapi_serp(kw_text, clean_target, competitors)
                if pos_info:
                    position = pos_info.get("target_position")
                    ranking_url = pos_info.get("target_url")
                    serp_features = pos_info.get("features", [])
                    has_ai_overview = "ai_overview" in serp_features
                    has_snippet = "featured_snippet" in serp_features
                    has_local = "local_pack" in serp_features
                    comp_records = pos_info.get("competitors", [])

            # Compute rank delta: e.g. was 35, now 18 -> delta = +17
            delta = 0
            if prev_pos is not None and position is not None:
                delta = prev_pos - position
            elif prev_pos is None and position is not None:
                delta = 0

            # Record history
            self.store.record_keyword_serp_history({
                "keyword_id": kw_id,
                "project_id": project_id,
                "domain": clean_target,
                "position": position,
                "previous_position": prev_pos,
                "position_delta": delta,
                "ranking_url": ranking_url,
                "serp_features": serp_features,
                "has_ai_overview": has_ai_overview,
                "has_featured_snippet": has_snippet,
                "has_local_pack": has_local,
                "snapshot_date": today,
                "raw_serp_ref": "live_serp_provider" if (has_dataforseo or has_serpapi) else "unconfigured_provider",
            })

            # Record competitor positions
            if comp_records:
                for c in comp_records:
                    c["keyword_id"] = kw_id
                    c["project_id"] = project_id
                    c["snapshot_date"] = today
                self.store.record_keyword_competitors(comp_records)

            synced_count += 1
            updated = self.store.get_project_keyword(kw_id)
            if updated:
                updated_keywords.append(TrackedKeyword(**updated))

        summary = self.calculate_movement_summary(updated_keywords)

        return {
            "synced_count": synced_count,
            "date": today,
            "summary": summary.model_dump(),
            "has_live_credentials": has_dataforseo or has_serpapi,
        }

    def calculate_movement_summary(self, keywords: List[TrackedKeyword]) -> KeywordMovementSummary:
        total = len(keywords)
        improved = 0
        declined = 0
        stable = 0
        top_3 = 0
        top_10 = 0
        ai_overview = 0
        breakouts: List[TrackedKeyword] = []
        drops: List[TrackedKeyword] = []

        for kw in keywords:
            curr = kw.current_position
            prev = kw.previous_position
            delta = kw.position_delta

            if kw.has_ai_overview:
                ai_overview += 1

            if curr is not None:
                if curr <= 3:
                    top_3 += 1
                if curr <= 10:
                    top_10 += 1

                # Page 1 breakout: was > 10, now <= 10
                if prev is not None and prev > 10 and curr <= 10:
                    breakouts.append(kw)

                if delta > 0:
                    improved += 1
                elif delta < 0:
                    declined += 1
                    if abs(delta) >= 5:
                        drops.append(kw)
                else:
                    stable += 1
            else:
                stable += 1

        return KeywordMovementSummary(
            total_tracked=total,
            improved_count=improved,
            declined_count=declined,
            stable_count=stable,
            top_3_count=top_3,
            top_10_count=top_10,
            page_1_breakouts=breakouts,
            significant_drops=drops,
            ai_overview_count=ai_overview,
        )

    def _query_dataforseo_serp(
        self,
        keyword: str,
        target_domain: str,
        competitor_domains: List[str],
    ) -> Optional[Dict[str, Any]]:
        import httpx
        try:
            res = httpx.post(
                "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                json=[{"keyword": keyword, "location_code": 2840, "language_code": "en", "depth": 100}],
                auth=(settings.DATAFORSEO_LOGIN or "", settings.DATAFORSEO_PASSWORD or ""),
                timeout=15.0,
            )
            if res.status_code != 200:
                return None
            data = res.json()
            tasks = data.get("tasks") or []
            if not tasks or not tasks[0].get("result"):
                return None
            items = tasks[0]["result"][0].get("items") or []

            target_pos = None
            target_url = None
            features: set[str] = set()
            comp_positions: List[Dict[str, Any]] = []

            for item in items:
                i_type = item.get("type")
                if i_type == "featured_snippet":
                    features.add("featured_snippet")
                elif i_type in {"ai_overview", "generative_summary"}:
                    features.add("ai_overview")
                elif i_type in {"local_pack", "maps_search"}:
                    features.add("local_pack")
                elif i_type == "people_also_ask":
                    features.add("people_also_ask")
                elif i_type == "video":
                    features.add("video")

                if i_type == "organic":
                    item_domain = _clean_domain(item.get("domain", ""))
                    rank = item.get("rank_group")
                    if item_domain == target_domain and target_pos is None:
                        target_pos = rank
                        target_url = item.get("url")

                    for comp in competitor_domains:
                        if item_domain == comp:
                            comp_positions.append({
                                "competitor_domain": comp,
                                "position": rank,
                                "ranking_url": item.get("url"),
                            })

            return {
                "target_position": target_pos,
                "target_url": target_url,
                "features": list(features),
                "competitors": comp_positions,
            }
        except Exception as exc:
            logger.warning("DataForSEO live SERP query failed for '%s': %s", keyword, exc)
            return None

    def _query_serpapi_serp(
        self,
        keyword: str,
        target_domain: str,
        competitor_domains: List[str],
    ) -> Optional[Dict[str, Any]]:
        import httpx
        try:
            res = httpx.get(
                "https://serpapi.com/search.json",
                params={"engine": "google", "q": keyword, "api_key": settings.SERPAPI_KEY, "num": 100},
                timeout=15.0,
            )
            if res.status_code != 200:
                return None
            data = res.json()
            organic = data.get("organic_results") or []
            features: set[str] = set()

            if "answer_box" in data:
                features.add("featured_snippet")
            if "ai_overview" in data or "generative_ai" in data:
                features.add("ai_overview")
            if "local_results" in data or "places" in data:
                features.add("local_pack")
            if "related_questions" in data:
                features.add("people_also_ask")

            target_pos = None
            target_url = None
            comp_positions: List[Dict[str, Any]] = []

            for item in organic:
                item_domain = _clean_domain(item.get("link", ""))
                rank = item.get("position")
                if item_domain == target_domain and target_pos is None:
                    target_pos = rank
                    target_url = item.get("link")

                for comp in competitor_domains:
                    if item_domain == comp:
                        comp_positions.append({
                            "competitor_domain": comp,
                            "position": rank,
                            "ranking_url": item.get("link"),
                        })

            return {
                "target_position": target_pos,
                "target_url": target_url,
                "features": list(features),
                "competitors": comp_positions,
            }
        except Exception as exc:
            logger.warning("SerpAPI query failed for '%s': %s", keyword, exc)
            return None


serp_tracking_engine = SerpTrackingEngine()
