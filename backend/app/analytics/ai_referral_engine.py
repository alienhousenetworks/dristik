"""
AI Referral Analytics & Attribution Engine.

Identifies visitors arriving from AI platforms (ChatGPT, Perplexity, Gemini, Claude,
Copilot, Google AI Overviews where identifiable, and other AI referrers), tracks their
website journey, and attributes conversions & reconciled revenue using First-Touch,
Last-Touch, and Assisted models.

Strict Truthfulness Contract:
- An AI answer citing a site does NOT prove a visitor clicked it.
- Not every AI referral carries a recognizable HTTP referrer.
- Explicitly separates: observed referrals, attributed conversions, assisted conversions,
  and unobservable/unknown traffic. Never estimates missing traffic as measured traffic.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit
from pydantic import BaseModel, Field

from app.db.enterprise_intelligence_schema import connect_enterprise_db
from app.governance.data_reliability import normalize_currency, normalize_timestamp_utc, utc_now_iso

AI_PLATFORM_REFERRERS: Dict[str, str] = {
    "chatgpt.com": "ChatGPT",
    "chat.openai.com": "ChatGPT",
    "perplexity.ai": "Perplexity",
    "labs.perplexity.ai": "Perplexity",
    "gemini.google.com": "Gemini",
    "bard.google.com": "Gemini",
    "claude.ai": "Claude",
    "copilot.microsoft.com": "Copilot",
    "edgeservices.bing.com": "Copilot",
    "poe.com": "Other AI",
    "you.com": "Other AI",
    "phind.com": "Other AI",
    "kagi.com": "Other AI",
    "meta.ai": "Other AI",
}

AI_UTM_SOURCES: Dict[str, str] = {
    "chatgpt": "ChatGPT",
    "openai": "ChatGPT",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
    "claude": "Claude",
    "anthropic": "Claude",
    "copilot": "Copilot",
    "google_ai_overviews": "Google AI Overviews",
    "ai_overview": "Google AI Overviews",
}


def classify_ai_traffic(
    http_referrer: Optional[str] = None,
    utm_source: Optional[str] = None,
    utm_medium: Optional[str] = None,
    landing_page: Optional[str] = None,
) -> Tuple[Optional[str], str, float]:
    """Classify a session's AI source.
    Returns `(ai_platform_or_None, visibility_state, attribution_confidence)`.
    visibility_state: OBSERVED_REFERRER | OBSERVED_UTM | OBSERVED_AIO_FRAGMENT | DIRECT_OR_UNKNOWN
    """
    ref = (http_referrer or "").strip()
    if ref:
        host = (urlsplit(ref).hostname or ref.split("/")[0]).lower().lstrip(".")
        for dom, platform in AI_PLATFORM_REFERRERS.items():
            if host == dom or host.endswith("." + dom):
                return platform, "OBSERVED_REFERRER", 0.98
        # Google AI Overviews sometimes arrive with google.* referrer + #:~:text= fragment on landing URL
        if ("google." in host) and landing_page and "#:~:text=" in landing_page:
            return "Google AI Overviews", "OBSERVED_AIO_FRAGMENT", 0.72

    u_src = (utm_source or "").strip().lower()
    if u_src in AI_UTM_SOURCES:
        return AI_UTM_SOURCES[u_src], "OBSERVED_UTM", 0.92
    if (utm_medium or "").strip().lower() in {"ai", "ai_referral", "llm"} and u_src:
        return u_src.title(), "OBSERVED_UTM", 0.85

    return None, "DIRECT_OR_UNKNOWN", 0.0


class AiReferralDashboardSummary(BaseModel):
    org_id: str
    domain: str
    status: str  # MEASURED | NO_OBSERVED_SESSIONS
    ai_referred_sessions: int = 0
    unknown_or_unobservable_sessions: int = 0
    ai_attributed_conversions: int = 0
    ai_assisted_conversions: int = 0
    ai_attributed_revenue: float = 0.0
    base_currency: str = "INR"
    revenue_per_ai_session: Optional[float] = None
    new_visitors: int = 0
    returning_visitors: int = 0
    by_source: List[Dict[str, Any]] = Field(default_factory=list)
    top_landing_pages: List[Dict[str, Any]] = Field(default_factory=list)
    daily_trends: List[Dict[str, Any]] = Field(default_factory=list)
    disclosure: str = (
        "Counts strictly reflect observed AI referrers, UTMs, and reconciled conversions. "
        "Unobservable AI-influenced visits without referrer metadata are disclosed separately and never estimated."
    )


class AiReferralEngine:
    """Ingests sessions & conversions, computes First/Last/Assisted attribution, and reconciles revenue."""

    @classmethod
    def record_session(
        cls,
        *,
        org_id: str,
        domain: str,
        session_id: str,
        visitor_id: str,
        landing_page: str,
        http_referrer: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        device_category: str = "desktop",
        is_new_visitor: bool = True,
        is_bot_or_internal: bool = False,
        consent_analytics: bool = True,
        started_at_utc: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts_utc, tz_label = normalize_timestamp_utc(started_at_utc)
        ai_platform, visibility, confidence = classify_ai_traffic(
            http_referrer=http_referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            landing_page=landing_page,
        )
        conn = connect_enterprise_db(db_path)
        try:
            # Idempotent session deduplication
            conn.execute(
                """
                INSERT OR IGNORE INTO visitor_sessions (
                    session_id, org_id, domain, visitor_id, landing_page, http_referrer,
                    utm_source, utm_medium, utm_campaign, ai_platform, attribution_visibility,
                    device_category, is_new_visitor, is_bot_or_internal, consent_analytics,
                    started_at_utc, timezone_offset
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, org_id, domain, visitor_id, landing_page, http_referrer,
                    utm_source, utm_medium, utm_campaign, ai_platform, visibility,
                    device_category.lower(), int(is_new_visitor), int(is_bot_or_internal),
                    int(consent_analytics), ts_utc, tz_label,
                ),
            )
            if not is_bot_or_internal and consent_analytics:
                cnt_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM attribution_touchpoints WHERE org_id = ? AND visitor_id = ?",
                    (org_id, visitor_id),
                ).fetchone()
                order_num = int(cnt_row["c"]) + 1
                channel = f"AI:{ai_platform}" if ai_platform else (utm_medium or "direct_or_other")
                conn.execute(
                    """
                    INSERT OR IGNORE INTO attribution_touchpoints (
                        touchpoint_id, org_id, visitor_id, session_id, channel, ai_platform,
                        landing_page, touchpoint_order, touchpoint_ts_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"tp_{session_id}", org_id, visitor_id, session_id, channel,
                        ai_platform, landing_page, order_num, ts_utc,
                    ),
                )
            conn.commit()
        finally:
            conn.close()
        return {
            "session_id": session_id,
            "ai_platform": ai_platform,
            "attribution_visibility": visibility,
            "confidence": confidence,
        }

    @classmethod
    def record_conversion_and_attribute(
        cls,
        *,
        org_id: str,
        domain: str,
        event_id: str,
        visitor_id: str,
        session_id: Optional[str],
        event_name: str,
        funnel_type: str = "ecommerce",
        order_id: Optional[str] = None,
        monetary_value: Optional[float] = None,
        currency: str = "INR",
        base_currency: str = "INR",
        explicit_fx_rate: Optional[float] = None,
        event_ts_utc: Optional[str] = None,
        source_system: str = "sdk",
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deduplicates conversion by event_id, reconciles with order/refunds, and computes First/Last/Assisted attribution."""
        ev_ts, _ = normalize_timestamp_utc(event_ts_utc)
        now = utc_now_iso()
        norm_val: Optional[float] = None
        fx_rate = 1.0
        if monetary_value is not None:
            norm_val, fx_rate, base_currency = normalize_currency(
                monetary_value, currency, base_currency, explicit_fx_rate
            )

        conn = connect_enterprise_db(db_path)
        try:
            # Deduplicate conversion event by stable event_id
            exists = conn.execute(
                "SELECT event_id FROM conversion_events WHERE event_id = ?", (event_id,)
            ).fetchone()
            if exists:
                return {"event_id": event_id, "deduplicated": True, "attributions": []}

            # Reconcile against confirmed transaction & refunds when order_id is provided
            reconciled = 0
            effective_revenue = norm_val or 0.0
            if order_id:
                tx = conn.execute(
                    "SELECT net_amount, currency, status FROM transactions WHERE org_id = ? AND order_id = ? LIMIT 1",
                    (org_id, order_id),
                ).fetchone()
                if tx:
                    if str(tx["status"]).upper() == "CANCELLED":
                        effective_revenue = 0.0
                    else:
                        tx_norm, _, _ = normalize_currency(float(tx["net_amount"]), tx["currency"], base_currency)
                        refunds = conn.execute(
                            "SELECT COALESCE(SUM(refund_amount), 0) AS r FROM transaction_refunds WHERE org_id = ? AND order_id = ?",
                            (org_id, order_id),
                        ).fetchone()
                        ref_amt = float(refunds["r"] or 0.0)
                        effective_revenue = max(0.0, round(tx_norm - ref_amt, 2))
                    reconciled = 1

            conn.execute(
                """
                INSERT INTO conversion_events (
                    event_id, org_id, domain, visitor_id, session_id, event_name, funnel_type,
                    order_id, monetary_value, currency, normalized_value_base, base_currency,
                    fx_rate, event_ts_utc, ingested_at_utc, source_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, org_id, domain, visitor_id, session_id, event_name, funnel_type,
                    order_id, monetary_value, currency.upper(), effective_revenue, base_currency,
                    fx_rate, ev_ts, now, source_system,
                ),
            )

            # Fetch visitor touchpoints in chronological order
            tps = conn.execute(
                """
                SELECT session_id, ai_platform, touchpoint_order
                FROM attribution_touchpoints
                WHERE org_id = ? AND visitor_id = ?
                ORDER BY touchpoint_ts_utc ASC, touchpoint_order ASC
                """,
                (org_id, visitor_id),
            ).fetchall()

            attributions: List[Dict[str, Any]] = []
            if tps:
                first_tp = tps[0]
                last_tp = tps[-1]
                # First-touch
                if first_tp["ai_platform"]:
                    attributions.append({
                        "model_name": "first_touch",
                        "ai_platform": first_tp["ai_platform"],
                        "attributed_revenue": effective_revenue,
                        "confidence": 0.90 if reconciled else 0.75,
                        "is_assisted": 0,
                    })
                # Last-touch
                if last_tp["ai_platform"]:
                    attributions.append({
                        "model_name": "last_touch",
                        "ai_platform": last_tp["ai_platform"],
                        "attributed_revenue": effective_revenue,
                        "confidence": 0.95 if reconciled else 0.80,
                        "is_assisted": 0,
                    })
                # Assisted (any AI touchpoint that is NOT the last touchpoint)
                assisted_platforms = {
                    tp["ai_platform"] for tp in tps[:-1] if tp["ai_platform"]
                }
                for plat in sorted(assisted_platforms):
                    attributions.append({
                        "model_name": "assisted",
                        "ai_platform": plat,
                        "attributed_revenue": round(effective_revenue / max(len(tps), 1), 2),
                        "confidence": 0.70,
                        "is_assisted": 1,
                    })

            for attr in attributions:
                conn.execute(
                    """
                    INSERT INTO revenue_attributions (
                        attribution_id, org_id, conversion_event_id, order_id, model_name,
                        ai_platform, attributed_revenue, currency, attribution_confidence,
                        is_assisted, reconciled_with_order, computed_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"attr_{uuid.uuid4().hex[:12]}", org_id, event_id, order_id,
                        attr["model_name"], attr["ai_platform"], attr["attributed_revenue"],
                        base_currency, attr["confidence"], attr["is_assisted"], reconciled, now,
                    ),
                )
            conn.commit()
            return {
                "event_id": event_id,
                "deduplicated": False,
                "reconciled_with_order": bool(reconciled),
                "effective_revenue": effective_revenue,
                "attributions": attributions,
            }
        finally:
            conn.close()

    @classmethod
    def get_dashboard_summary(
        cls,
        *,
        org_id: str,
        domain: str,
        model_name: str = "last_touch",
        base_currency: str = "INR",
        db_path: Optional[str] = None,
    ) -> AiReferralDashboardSummary:
        conn = connect_enterprise_db(db_path)
        try:
            sess_rows = conn.execute(
                """
                SELECT ai_platform, landing_page, is_new_visitor, substr(started_at_utc, 1, 10) AS day
                FROM visitor_sessions
                WHERE org_id = ? AND domain = ? AND is_bot_or_internal = 0 AND consent_analytics = 1
                """,
                (org_id, domain),
            ).fetchall()

            ai_sessions = 0
            unknown_sessions = 0
            new_v = 0
            ret_v = 0
            by_plat: Dict[str, Dict[str, Any]] = {}
            by_lp: Dict[str, int] = {}
            by_day: Dict[str, int] = {}

            for r in sess_rows:
                plat = r["ai_platform"]
                if not plat:
                    unknown_sessions += 1
                    continue
                ai_sessions += 1
                if r["is_new_visitor"]:
                    new_v += 1
                else:
                    ret_v += 1
                entry = by_plat.setdefault(plat, {"ai_platform": plat, "sessions": 0, "conversions": 0, "assisted_conversions": 0, "revenue": 0.0})
                entry["sessions"] += 1
                by_lp[r["landing_page"]] = by_lp.get(r["landing_page"], 0) + 1
                by_day[r["day"]] = by_day.get(r["day"], 0) + 1

            attr_rows = conn.execute(
                """
                SELECT ra.model_name, ra.ai_platform, ra.attributed_revenue, ra.is_assisted
                FROM revenue_attributions ra
                JOIN conversion_events ce ON ce.event_id = ra.conversion_event_id
                WHERE ra.org_id = ? AND ce.domain = ?
                """,
                (org_id, domain),
            ).fetchall()

            total_conv = 0
            total_assisted = 0
            total_rev = 0.0
            for ar in attr_rows:
                plat = ar["ai_platform"]
                if not plat:
                    continue
                entry = by_plat.setdefault(plat, {"ai_platform": plat, "sessions": 0, "conversions": 0, "assisted_conversions": 0, "revenue": 0.0})
                if ar["model_name"] == model_name:
                    total_conv += 1
                    total_rev += float(ar["attributed_revenue"] or 0.0)
                    entry["conversions"] += 1
                    entry["revenue"] = round(entry["revenue"] + float(ar["attributed_revenue"] or 0.0), 2)
                elif ar["is_assisted"]:
                    total_assisted += 1
                    entry["assisted_conversions"] += 1

            by_source = []
            for entry in sorted(by_plat.values(), key=lambda x: -x["sessions"]):
                s = entry["sessions"]
                entry["conversion_rate_pct"] = round((entry["conversions"] / s) * 100.0, 2) if s > 0 else None
                entry["revenue_per_session"] = round(entry["revenue"] / s, 2) if s > 0 else None
                by_source.append(entry)

            return AiReferralDashboardSummary(
                org_id=org_id,
                domain=domain,
                status="MEASURED" if ai_sessions > 0 else "NO_OBSERVED_SESSIONS",
                ai_referred_sessions=ai_sessions,
                unknown_or_unobservable_sessions=unknown_sessions,
                ai_attributed_conversions=total_conv,
                ai_assisted_conversions=total_assisted,
                ai_attributed_revenue=round(total_rev, 2),
                base_currency=base_currency,
                revenue_per_ai_session=round(total_rev / ai_sessions, 2) if ai_sessions > 0 else None,
                new_visitors=new_v,
                returning_visitors=ret_v,
                by_source=by_source,
                top_landing_pages=[{"landing_page": k, "ai_sessions": v} for k, v in sorted(by_lp.items(), key=lambda x: -x[1])[:15]],
                daily_trends=[{"date": k, "ai_sessions": v} for k, v in sorted(by_day.items())],
            )
        finally:
            conn.close()
