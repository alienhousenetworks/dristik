"""Search Console and SERP rows for the sealed audit.

Query-level advice is allowed only when one of those providers measured this
domain. A missing provider stays NOT_CONNECTED. This module does not invent
volume, rank, or a keyword gap.
"""
from __future__ import annotations

import logging
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


def build_search_demand(
    search_console: Optional[Dict[str, Any]] = None,
    serp_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Assemble the blackboard payload from already-mapped provider rows."""
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

    sources = []
    if queries:
        sources.append("google_search_console")
    if measured_serp:
        sources.append("serp_tracker")
    status = "MEASURED" if sources else "NOT_CONNECTED"
    if status == "MEASURED":
        note = (
            "Query and rank rows from "
            + " and ".join(sources)
            + " are attached. Query-level advice may cite only these rows."
        )
    else:
        note = (
            "Search Console and SERP rows were not measured for this audit. "
            "Query-level advice is skipped."
        )
    return {
        "status": status,
        "sources": sources,
        "queries": queries,
        "serp_rows": measured_serp,
        "note": note,
    }


def load_search_demand(domain: str) -> Dict[str, Any]:
    """Read connected providers. A connector error leaves the demand unmeasured."""
    channel: Dict[str, Any] = {"state": "NOT_CONNECTED"}
    try:
        from app.integrations.google_report import load_search_console, map_search_console
        channel = map_search_console(load_search_console(domain))
    except Exception as exc:
        logger.info("Search Console demand was not loaded: %s", exc)
        channel = {"state": "NOT_CONNECTED"}

    serp_rows: List[Dict[str, Any]] = []
    host = _domain(domain)
    if host:
        try:
            from app.connectors.authority.store import ExternalStore
            serp_rows = ExternalStore().list_measured_keywords_for_domain(host)
        except Exception as exc:
            logger.info("SERP demand was not loaded: %s", exc)
            serp_rows = []
    return build_search_demand(channel, serp_rows)


def attach_search_demand(blackboard: Any, domain: str) -> Dict[str, Any]:
    """Put provider rows on the blackboard before the specialist waves."""
    demand = load_search_demand(domain)
    state = getattr(blackboard, "blackboard_state", None)
    if isinstance(state, dict):
        state["search_demand"] = demand
    return demand
