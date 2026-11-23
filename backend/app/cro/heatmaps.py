"""
Behavioral Heatmap Aggregation Engine (Click, Scroll, Movement, Estimated Engagement).

Strict Enterprise Guarantees:
- Normalizes coordinates against viewport dimensions (0.0 - 1.0 grid bins).
- Associates interactions with page URL, DOM selector, and device (desktop / tablet / mobile).
- Enforces explicit session denominators before reporting any scroll-depth insight.
- Explicitly labels movement/attention heatmaps as cursor/interaction concentration —
  NEVER described as eye-tracking or true visual attention.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.db.enterprise_intelligence_schema import connect_enterprise_db


class HeatmapReport(BaseModel):
    org_id: str
    domain: str
    page_url: str
    device_category: str
    status: str  # MEASURED | NO_TELEMETRY
    denominator_sessions: int = 0
    click_points: List[Dict[str, Any]] = Field(default_factory=list)
    dead_click_points: List[Dict[str, Any]] = Field(default_factory=list)
    scroll_depth_distribution: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    movement_concentration_label: str = "Estimated cursor/interaction concentration (NOT eye-tracking)"
    selector_engagement: List[Dict[str, Any]] = Field(default_factory=list)
    scroll_insights: List[str] = Field(default_factory=list)


class HeatmapEngine:
    """Aggregates real browser telemetry into viewport-normalized click, scroll, and selector heatmaps."""

    @classmethod
    def build_page_heatmap(
        cls,
        *,
        org_id: str,
        domain: str,
        page_url: str,
        device_category: str = "desktop",
        db_path: Optional[str] = None,
    ) -> HeatmapReport:
        dev = device_category.lower()
        conn = connect_enterprise_db(db_path)
        try:
            rows = conn.execute(
                """
                SELECT session_id, event_name, click_x, click_y, scroll_depth_pct,
                       dom_selector, is_dead_click, is_rage_click
                FROM analytics_events
                WHERE org_id = ? AND domain = ? AND page_url = ? AND device_category = ?
                  AND is_bot_or_internal = 0 AND consent_granted = 1
                """,
                (org_id, domain, page_url, dev),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return HeatmapReport(
                org_id=org_id, domain=domain, page_url=page_url, device_category=dev, status="NO_TELEMETRY"
            )

        all_sessions = {r["session_id"] for r in rows}
        denom = len(all_sessions)
        click_bins: Dict[tuple[float, float], int] = {}
        dead_bins: Dict[tuple[float, float], int] = {}
        sel_counts: Dict[str, int] = {}
        max_scroll_per_session: Dict[str, float] = {sid: 0.0 for sid in all_sessions}

        for r in rows:
            if r["event_name"] == "click" and r["click_x"] is not None and r["click_y"] is not None:
                bx = round(float(r["click_x"]) * 20) / 20.0
                by = round(float(r["click_y"]) * 20) / 20.0
                click_bins[(bx, by)] = click_bins.get((bx, by), 0) + 1
                if r["is_dead_click"]:
                    dead_bins[(bx, by)] = dead_bins.get((bx, by), 0) + 1
                if r["dom_selector"]:
                    sel_counts[r["dom_selector"]] = sel_counts.get(r["dom_selector"], 0) + 1
            if r["scroll_depth_pct"] is not None:
                sid = r["session_id"]
                max_scroll_per_session[sid] = max(max_scroll_per_session.get(sid, 0.0), float(r["scroll_depth_pct"]))

        scroll_dist: Dict[str, Dict[str, Any]] = {}
        insights: List[str] = []
        for milestone in (25, 50, 75, 90, 100):
            reached = sum(1 for v in max_scroll_per_session.values() if v >= milestone)
            pct = round((reached / denom) * 100.0, 1)
            scroll_dist[f"{milestone}%"] = {"sessions_reached": reached, "denominator_sessions": denom, "pct_reached": pct}
            if milestone == 75 and pct < 50.0:
                insights.append(
                    f"{round(100.0 - pct, 1)}% of {dev} visitors ({denom - reached}/{denom} sessions) do not reach 75% scroll depth on {page_url}."
                )

        return HeatmapReport(
            org_id=org_id,
            domain=domain,
            page_url=page_url,
            device_category=dev,
            status="MEASURED",
            denominator_sessions=denom,
            click_points=[{"x_norm": x, "y_norm": y, "count": c} for (x, y), c in sorted(click_bins.items(), key=lambda kv: -kv[1])],
            dead_click_points=[{"x_norm": x, "y_norm": y, "count": c} for (x, y), c in sorted(dead_bins.items(), key=lambda kv: -kv[1])],
            scroll_depth_distribution=scroll_dist,
            selector_engagement=[{"dom_selector": s, "clicks": c} for s, c in sorted(sel_counts.items(), key=lambda kv: -kv[1])[:25]],
            scroll_insights=insights,
        )
