"""Search Console, DataForSEO, and on-page crawl topic seeds for the sealed audit.

Query-level search volume advice is allowed only when Search Console or DataForSEO
measured this domain. When neither provider is configured/connected, status is
returned as NOT_CONFIGURED alongside the extracted on-page topic/intent clusters
(clearly distinguishing observed on-page topic targeting from unmeasured external search volume).
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("dristik.search_demand")


def _domain(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    return urlparse(raw).netloc.replace("www.", "").split(":")[0]


def _classify_intent(phrase: str) -> str:
    low = phrase.lower()
    if any(k in low for k in ("buy", "price", "pricing", "cost", "shop", "order", "bundle", "kit", "discount", "offer", "plan")):
        return "Transactional / Commercial"
    if any(k in low for k in ("vs", "compare", "alternative", "best", "top", "review", "rating")):
        return "Commercial Investigation"
    if any(k in low for k in ("how", "what", "why", "guide", "benefits", "ingredients", "instructions", "faq")):
        return "Informational"
    return "Commercial / Navigational"


def extract_crawl_topic_seeds(
    pages: Optional[List[Any]] = None,
    business_profile: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Extracts seed keywords and topic/intent clusters strictly from observed
    business_profile and crawled page titles, H1s, and H2s.
    Never fabricates external search volume.
    """
    seeds: List[str] = []
    topic_clusters: List[Dict[str, Any]] = []
    seen = set()

    def _add_seed(term: str, source: str, page_url: Optional[str] = None):
        cleaned = re.sub(r"\s+", " ", (term or "").strip())
        cleaned = cleaned.strip("|-–—:•· ")
        if not cleaned or len(cleaned) < 3 or len(cleaned) > 90:
            return
        norm = cleaned.lower()
        if norm in {"home", "welcome", "index", "untitled", "unknown", "unknown business"}:
            return
        if norm not in seen:
            seen.add(norm)
            seeds.append(cleaned)
            topic_clusters.append({
                "topic": cleaned,
                "intent": _classify_intent(cleaned),
                "source": source,
                "target_url": page_url,
                "search_volume": None,
                "volume_status": "UNMEASURED_EXTERNAL_VOLUME",
            })

    if business_profile:
        for attr in ("niche", "sub_niche", "industry"):
            val = getattr(business_profile, attr, None)
            if val:
                _add_seed(str(val), f"business_profile.{attr}")
        for list_attr in ("products", "services"):
            for item in (getattr(business_profile, list_attr, None) or []):
                if item:
                    _add_seed(str(item), f"business_profile.{list_attr}")

    for p in (pages or []):
        p_url = getattr(p, "url", None) if not isinstance(p, dict) else p.get("url")
        title = getattr(p, "title", None) if not isinstance(p, dict) else p.get("title")
        h1s = (getattr(p, "h1", None) if not isinstance(p, dict) else p.get("h1")) or []
        h2s = (getattr(p, "h2", None) if not isinstance(p, dict) else p.get("h2")) or []

        if title:
            for seg in re.split(r"[|\-–—:]", str(title)):
                _add_seed(seg, "page_title", p_url)
        for h1 in h1s[:3]:
            _add_seed(str(h1), "page_h1", p_url)
        for h2 in h2s[:5]:
            _add_seed(str(h2), "page_h2", p_url)

    return {
        "seed_keywords": seeds[:25],
        "on_page_topic_clusters": topic_clusters[:25],
        "measurement_disclaimer": (
            "On-page topic clusters are observed from crawled DOM titles/headings and BusinessProfile. "
            "External monthly search volume is unmeasured unless Search Console or DataForSEO is connected."
        ),
    }


def build_search_demand(
    search_console: Optional[Dict[str, Any]] = None,
    serp_rows: Optional[List[Dict[str, Any]]] = None,
    dataforseo_keywords: Optional[List[Dict[str, Any]]] = None,
    crawl_topics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Assemble the blackboard payload from already-mapped provider rows and on-page topic clusters."""
    channel = search_console or {}
    queries: List[Dict[str, Any]] = []
    if channel.get("state") == "MEASURED":
        for row in channel.get("queries") or []:
            query = (row.get("query") or "").strip()
            if not query:
                continue
            queries.append({
                "query": query,
                "page": row.get("page") or "",
                "clicks": row.get("clicks"),
                "impressions": row.get("impressions"),
                "ctr": row.get("ctr"),
                "position": row.get("position"),
                "source": "google_search_console",
            })

    measured_serp = []
    for row in serp_rows or []:
        if row.get("position") is None and row.get("current_position") is None:
            continue
        measured_serp.append({
            "keyword": row.get("keyword") or row.get("query") or "",
            "position": row.get("position") if row.get("position") is not None else row.get("current_position"),
            "page": row.get("target_url") or row.get("page") or "",
            "source": row.get("source") or "serp_tracker",
        })
    measured_serp = [row for row in measured_serp if row["keyword"]]

    measured_keywords = list(dataforseo_keywords or [])

    sources = []
    if queries:
        sources.append("google_search_console")
    if measured_serp:
        sources.append("serp_tracker")
    if measured_keywords:
        sources.append("dataforseo")

    status = "MEASURED" if sources else "NOT_CONFIGURED"
    if status == "MEASURED":
        note = (
            "Query and rank rows from "
            + " and ".join(sources)
            + " are attached. Query-level advice may cite only these rows."
        )
    else:
        note = (
            "Search Console and DataForSEO keyword volume providers are NOT_CONFIGURED for this audit. "
            "On-page topic clusters are extracted from crawled headings/titles; external search volume is unmeasured."
        )

    topics_payload = crawl_topics or {"seed_keywords": [], "on_page_topic_clusters": []}
    return {
        "status": status,
        "sources": sources,
        "queries": queries,
        "serp_rows": measured_serp,
        "keyword_metrics": measured_keywords,
        "seed_keywords": topics_payload.get("seed_keywords", []),
        "on_page_topic_clusters": topics_payload.get("on_page_topic_clusters", []),
        "note": note,
    }


def load_search_demand(
    domain: str,
    pages: Optional[List[Any]] = None,
    business_profile: Optional[Any] = None,
) -> Dict[str, Any]:
    """Read connected providers and extract on-page topic clusters."""
    crawl_topics = extract_crawl_topic_seeds(pages=pages, business_profile=business_profile)
    channel: Dict[str, Any] = {"state": "NOT_CONNECTED"}
    try:
        from app.integrations.google_report import load_search_console, map_search_console
        channel = map_search_console(load_search_console(domain))
    except Exception as exc:
        logger.info("Search Console demand was not loaded: %s", exc)
        channel = {"state": "NOT_CONNECTED"}

    serp_rows: List[Dict[str, Any]] = []
    dataforseo_rows: List[Dict[str, Any]] = []
    host = _domain(domain)
    if host:
        try:
            from app.connectors.authority.store import ExternalStore
            serp_rows = ExternalStore().list_measured_keywords_for_domain(host)
        except Exception as exc:
            logger.info("SERP demand was not loaded: %s", exc)
            serp_rows = []

        try:
            from app.connectors.dataforseo.dataforseo_provider import KeywordAndBacklinkProvider
            dfs_provider = KeywordAndBacklinkProvider()
            if dfs_provider.is_connected:
                seeds = crawl_topics.get("seed_keywords") or None
                dfs_res = dfs_provider.fetch_keywords(host, seed_keywords=seeds)
                if dfs_res and dfs_res.keywords:
                    dataforseo_rows = [
                        k.model_dump() if hasattr(k, "model_dump") else dict(k)
                        for k in dfs_res.keywords
                    ]
        except Exception as exc:
            logger.info("DataForSEO keyword fetch skipped: %s", exc)
            dataforseo_rows = []

    return build_search_demand(
        search_console=channel,
        serp_rows=serp_rows,
        dataforseo_keywords=dataforseo_rows,
        crawl_topics=crawl_topics,
    )


def attach_search_demand(blackboard: Any, domain: str) -> Dict[str, Any]:
    """Put provider rows and on-page topic clusters on the blackboard before the specialist waves."""
    pages = getattr(blackboard, "pages", None)
    business_profile = getattr(blackboard, "business_profile", None)
    demand = load_search_demand(domain, pages=pages, business_profile=business_profile)
    state = getattr(blackboard, "blackboard_state", None)
    if isinstance(state, dict):
        state["search_demand"] = demand
    return demand
