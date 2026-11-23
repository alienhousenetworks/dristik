"""
Universal Conversion Attribution, Funnel Drop-Off & Cohort Analytics Engine.

Supports:
- Ecommerce funnel: page_view -> view_item -> add_to_cart -> begin_checkout -> add_payment_info -> purchase
- Lead-gen funnel: page_view -> form_start -> form_submit -> qualified_lead -> opportunity -> closed_won
  (Form submission is NEVER treated as revenue.)
- Stable event_id deduplication, out-of-order watermarking, bot/internal filtering,
  Mobile/Tablet/Desktop segmentation, Shopify/WooCommerce order+refund reconciliation,
  and SDK performance monitoring.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from app.db.enterprise_intelligence_schema import connect_enterprise_db
from app.governance.data_reliability import DataReliabilityGovernance, normalize_currency, normalize_timestamp_utc, utc_now_iso
from app.security.privacy_governance import sanitize_behavioral_payload

ECOMMERCE_FUNNEL_STEPS = ("page_view", "view_item", "add_to_cart", "begin_checkout", "add_payment_info", "purchase")
LEADGEN_FUNNEL_STEPS = ("page_view", "form_start", "form_submit", "qualified_lead", "opportunity", "closed_won")


class ConversionMetricsReport(BaseModel):
    org_id: str
    domain: str
    funnel_type: str
    device_filter: Optional[str] = None
    eligible_visitors: int = 0
    conversions: int = 0
    conversion_rate_pct: Optional[float] = None
    carts_created: int = 0
    cart_abandonment_rate_pct: Optional[float] = None
    checkout_starts: int = 0
    checkout_completion_rate_pct: Optional[float] = None
    qualified_leads: int = 0
    customers_won: int = 0
    lead_to_customer_rate_pct: Optional[float] = None
    reconciled_net_revenue: float = 0.0
    base_currency: str = "INR"
    revenue_per_visitor: Optional[float] = None
    average_order_value: Optional[float] = None
    orders_confirmed: int = 0
    refunds_total: float = 0.0
    funnel_steps: List[Dict[str, Any]] = Field(default_factory=list)
    by_device: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    avg_sdk_load_ms: Optional[float] = None
    disclosure: str = (
        "Excludes bots/internal traffic and non-consented sessions. "
        "Revenue reflects reconciled transactions net of refunds; form submissions are never counted as revenue."
    )


class ConversionAttributionEngine:
    """Ingests behavioral/conversion events and computes reconciled funnel & revenue metrics."""

    @classmethod
    def ingest_event(
        cls,
        *,
        org_id: str,
        domain: str,
        payload: Dict[str, Any],
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean = sanitize_behavioral_payload(payload)
        event_id = str(clean.get("event_id") or f"ev_{uuid.uuid4().hex[:14]}")
        consent_granted = bool(clean.get("consent_granted", True))
        if not consent_granted:
            return {"event_id": event_id, "accepted": False, "reason": "CONSENT_NOT_GRANTED"}

        ev_ts, _ = normalize_timestamp_utc(clean.get("event_ts_utc"))
        now = utc_now_iso()
        out_of_order = DataReliabilityGovernance.is_out_of_order_event(ev_ts, now)

        conn = connect_enterprise_db(db_path)
        try:
            exists = conn.execute("SELECT event_id FROM analytics_events WHERE event_id = ?", (event_id,)).fetchone()
            if exists:
                return {"event_id": event_id, "accepted": True, "deduplicated": True}

            device = str(clean.get("device_category") or "desktop").lower()
            if device not in {"mobile", "tablet", "desktop"}:
                device = "desktop"

            conn.execute(
                """
                INSERT INTO analytics_events (
                    event_id, org_id, domain, visitor_id, session_id, event_name, page_url,
                    device_category, viewport_w, viewport_h, click_x, click_y, scroll_depth_pct,
                    dom_selector, form_id, form_field_name, backend_submit_status,
                    is_rage_click, is_dead_click, is_bot_or_internal, consent_granted,
                    sdk_load_ms, event_ts_utc, ingested_at_utc, is_out_of_order, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, org_id, domain,
                    str(clean.get("visitor_id") or "anon"),
                    str(clean.get("session_id") or "sess"),
                    str(clean.get("event_name") or "page_view"),
                    str(clean.get("page_url") or "/"),
                    device,
                    clean.get("viewport_w"), clean.get("viewport_h"),
                    clean.get("click_x"), clean.get("click_y"), clean.get("scroll_depth_pct"),
                    clean.get("dom_selector"), clean.get("form_id"), clean.get("form_field_name"),
                    clean.get("backend_submit_status"),
                    int(bool(clean.get("is_rage_click", False))),
                    int(bool(clean.get("is_dead_click", False))),
                    int(bool(clean.get("is_bot_or_internal", False))),
                    1,
                    clean.get("sdk_load_ms"),
                    ev_ts, now, int(out_of_order),
                    json.dumps(clean.get("metadata") or {}, default=str),
                ),
            )
            conn.commit()
            return {"event_id": event_id, "accepted": True, "deduplicated": False, "is_out_of_order": out_of_order}
        finally:
            conn.close()

    @classmethod
    def record_transaction(
        cls,
        *,
        org_id: str,
        domain: str,
        order_id: str,
        source_platform: str,
        gross_amount: float,
        net_amount: Optional[float] = None,
        currency: str = "INR",
        status: str = "CONFIRMED",
        visitor_id: Optional[str] = None,
        transacted_at_utc: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts, _ = normalize_timestamp_utc(transacted_at_utc)
        now = utc_now_iso()
        tx_id = f"tx_{uuid.uuid4().hex[:12]}"
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO transactions (
                    transaction_id, org_id, domain, order_id, source_platform, visitor_id,
                    gross_amount, net_amount, currency, status, transacted_at_utc, reconciled_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(org_id, order_id, source_platform) DO UPDATE SET
                    net_amount=excluded.net_amount,
                    status=excluded.status,
                    reconciled_at_utc=excluded.reconciled_at_utc
                """,
                (
                    tx_id, org_id, domain, order_id, source_platform.lower(), visitor_id,
                    float(gross_amount), float(net_amount if net_amount is not None else gross_amount),
                    currency.upper(), status.upper(), ts, now,
                ),
            )
            conn.commit()
            return {"order_id": order_id, "source_platform": source_platform.lower(), "status": status.upper()}
        finally:
            conn.close()

    @classmethod
    def record_refund(
        cls,
        *,
        org_id: str,
        order_id: str,
        source_platform: str,
        refund_amount: float,
        currency: str = "INR",
        reason: Optional[str] = None,
        refunded_at_utc: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts, _ = normalize_timestamp_utc(refunded_at_utc)
        rid = f"ref_{uuid.uuid4().hex[:12]}"
        conn = connect_enterprise_db(db_path)
        try:
            conn.execute(
                """
                INSERT INTO transaction_refunds (
                    refund_id, org_id, order_id, source_platform, refund_amount, currency, reason, refunded_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rid, org_id, order_id, source_platform.lower(), float(refund_amount), currency.upper(), reason, ts),
            )
            conn.commit()
            return {"refund_id": rid, "order_id": order_id, "refund_amount": float(refund_amount)}
        finally:
            conn.close()

    @classmethod
    def compute_funnel_metrics(
        cls,
        *,
        org_id: str,
        domain: str,
        funnel_type: str = "ecommerce",
        device_filter: Optional[str] = None,
        base_currency: str = "INR",
        db_path: Optional[str] = None,
    ) -> ConversionMetricsReport:
        steps = ECOMMERCE_FUNNEL_STEPS if funnel_type == "ecommerce" else LEADGEN_FUNNEL_STEPS
        conn = connect_enterprise_db(db_path)
        try:
            where = "org_id = ? AND domain = ? AND is_bot_or_internal = 0 AND consent_granted = 1"
            params: List[Any] = [org_id, domain]
            if device_filter:
                where += " AND device_category = ?"
                params.append(device_filter.lower())

            rows = conn.execute(
                f"SELECT visitor_id, event_name, device_category, sdk_load_ms FROM analytics_events WHERE {where}",
                params,
            ).fetchall()

            step_visitors: Dict[str, set[str]] = {s: set() for s in steps}
            dev_visitors: Dict[str, set[str]] = {"mobile": set(), "tablet": set(), "desktop": set()}
            dev_convs: Dict[str, set[str]] = {"mobile": set(), "tablet": set(), "desktop": set()}
            sdk_loads: List[float] = []
            conv_event = "purchase" if funnel_type == "ecommerce" else "closed_won"

            for r in rows:
                ev = r["event_name"]
                vid = r["visitor_id"]
                dev = r["device_category"] if r["device_category"] in dev_visitors else "desktop"
                if ev in step_visitors:
                    step_visitors[ev].add(vid)
                if ev == "page_view":
                    dev_visitors[dev].add(vid)
                if ev == conv_event:
                    dev_convs[dev].add(vid)
                if r["sdk_load_ms"] is not None:
                    sdk_loads.append(float(r["sdk_load_ms"]))

            eligible = len(step_visitors["page_view"])
            conversions = len(step_visitors[conv_event])

            # Reconciled transactions & refunds
            tx_rows = conn.execute(
                "SELECT order_id, net_amount, currency, status FROM transactions WHERE org_id = ? AND domain = ?",
                (org_id, domain),
            ).fetchall()
            confirmed_orders = [t for t in tx_rows if str(t["status"]).upper() == "CONFIRMED"]
            gross_confirmed = sum(
                normalize_currency(float(t["net_amount"]), t["currency"], base_currency)[0]
                for t in confirmed_orders
            )
            ref_rows = conn.execute(
                "SELECT refund_amount, currency FROM transaction_refunds WHERE org_id = ?",
                (org_id,),
            ).fetchall()
            total_refunds = sum(
                normalize_currency(float(r["refund_amount"]), r["currency"], base_currency)[0]
                for r in ref_rows
            )
            net_rev = max(0.0, round(gross_confirmed - total_refunds, 2))
            orders_cnt = len(confirmed_orders)

            funnel_out: List[Dict[str, Any]] = []
            prev_cnt: Optional[int] = None
            for s in steps:
                cnt = len(step_visitors[s])
                dropoff = round(((prev_cnt - cnt) / prev_cnt) * 100.0, 1) if (prev_cnt and prev_cnt > 0) else 0.0
                funnel_out.append({"step": s, "unique_visitors": cnt, "dropoff_from_prev_pct": max(0.0, dropoff)})
                prev_cnt = cnt

            carts = len(step_visitors.get("add_to_cart", set()))
            checkouts = len(step_visitors.get("begin_checkout", set()))
            purchases = len(step_visitors.get("purchase", set()))
            q_leads = len(step_visitors.get("qualified_lead", set()))
            won = len(step_visitors.get("closed_won", set()))

            by_device = {}
            for d_name in ("mobile", "tablet", "desktop"):
                dv = len(dev_visitors[d_name])
                dc = len(dev_convs[d_name])
                by_device[d_name] = {
                    "eligible_visitors": dv,
                    "conversions": dc,
                    "conversion_rate_pct": round((dc / dv) * 100.0, 2) if dv > 0 else None,
                }

            return ConversionMetricsReport(
                org_id=org_id,
                domain=domain,
                funnel_type=funnel_type,
                device_filter=device_filter,
                eligible_visitors=eligible,
                conversions=conversions,
                conversion_rate_pct=round((conversions / eligible) * 100.0, 2) if eligible > 0 else None,
                carts_created=carts,
                cart_abandonment_rate_pct=round(((carts - purchases) / carts) * 100.0, 2) if carts > 0 else None,
                checkout_starts=checkouts,
                checkout_completion_rate_pct=round((purchases / checkouts) * 100.0, 2) if checkouts > 0 else None,
                qualified_leads=q_leads,
                customers_won=won,
                lead_to_customer_rate_pct=round((won / q_leads) * 100.0, 2) if q_leads > 0 else None,
                reconciled_net_revenue=net_rev,
                base_currency=base_currency,
                revenue_per_visitor=round(net_rev / eligible, 2) if eligible > 0 else None,
                average_order_value=round(net_rev / orders_cnt, 2) if orders_cnt > 0 else None,
                orders_confirmed=orders_cnt,
                refunds_total=round(total_refunds, 2),
                funnel_steps=funnel_out,
                by_device=by_device,
                avg_sdk_load_ms=round(sum(sdk_loads) / len(sdk_loads), 2) if sdk_loads else None,
            )
        finally:
            conn.close()
