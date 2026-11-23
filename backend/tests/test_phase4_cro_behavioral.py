"""Tests for Phase 4: Event SDK (<15KB), Conversion Attribution, Replay Connectors, 6 Behavioral Agents & Heatmaps."""
import gzip
from pathlib import Path

from app.analytics.conversion_attribution import ConversionAttributionEngine
from app.connectors.replay.providers import MicrosoftClarityConnector, PostHogReplayConnector
from app.cro.behavioral_agents import BehavioralAgentSuite
from app.cro.heatmaps import HeatmapEngine


def test_sdk_performance_budget_and_privacy_guards():
    sdk_path = Path(__file__).resolve().parent.parent / "app" / "analytics" / "sdk" / "dristik-events.js"
    raw = sdk_path.read_bytes()
    gz_size = len(gzip.compress(raw))
    assert gz_size < 15 * 1024, f"SDK gzipped size {gz_size} exceeds 15KB budget"
    text = raw.decode("utf-8")
    assert "MASKED" in text
    assert "withdrawConsent" in text
    assert "sdk_load_ms" in text


def test_conversion_attribution_agents_and_heatmaps(tmp_path):
    db = str(tmp_path / "cro_behav.db")
    # Confirmed order + refund
    ConversionAttributionEngine.record_transaction(
        org_id="org_1", domain="perforacare.com", order_id="ORD-50", source_platform="shopify",
        gross_amount=1500, net_amount=1500, currency="INR", status="CONFIRMED", db_path=db,
    )
    ConversionAttributionEngine.record_refund(
        org_id="org_1", order_id="ORD-50", source_platform="shopify", refund_amount=200, currency="INR", db_path=db,
    )

    # Visitor 1 (mobile): views, rage clicks CTA, adds to cart, checks out, purchases
    for idx, ev in enumerate([
        {"event_id": "e1", "visitor_id": "v1", "session_id": "s1", "event_name": "page_view", "page_url": "/brush", "device_category": "mobile", "sdk_load_ms": 4.2},
        {"event_id": "e2", "visitor_id": "v1", "session_id": "s1", "event_name": "click", "page_url": "/brush", "device_category": "mobile", "click_x": 0.5, "click_y": 0.6, "dom_selector": "#buy-btn", "is_rage_click": True},
        {"event_id": "e3", "visitor_id": "v1", "session_id": "s1", "event_name": "scroll_depth", "page_url": "/brush", "device_category": "mobile", "scroll_depth_pct": 80},
        {"event_id": "e4", "visitor_id": "v1", "session_id": "s1", "event_name": "add_to_cart", "page_url": "/brush", "device_category": "mobile"},
        {"event_id": "e5", "visitor_id": "v1", "session_id": "s1", "event_name": "begin_checkout", "page_url": "/checkout", "device_category": "mobile"},
        {"event_id": "e6", "visitor_id": "v1", "session_id": "s1", "event_name": "purchase", "page_url": "/thank-you", "device_category": "mobile"},
        # Visitor 2 (mobile): views, shallow scroll, starts form, abandons
        {"event_id": "e7", "visitor_id": "v2", "session_id": "s2", "event_name": "page_view", "page_url": "/brush", "device_category": "mobile", "scroll_depth_pct": 25},
        {"event_id": "e8", "visitor_id": "v2", "session_id": "s2", "event_name": "form_field_focus", "page_url": "/brush", "device_category": "mobile", "form_id": "lead-form", "form_field_name": "pincode"},
        # Visitor 3 (mobile): shallow scroll (ensures >50% don't reach 75%)
        {"event_id": "e9", "visitor_id": "v3", "session_id": "s3", "event_name": "page_view", "page_url": "/brush", "device_category": "mobile", "scroll_depth_pct": 25},
        # Bot traffic -> MUST be excluded
        {"event_id": "e_bot", "visitor_id": "bot1", "session_id": "s_bot", "event_name": "page_view", "page_url": "/brush", "device_category": "desktop", "is_bot_or_internal": True},
        # Non-consented -> MUST be rejected
        {"event_id": "e_nc", "visitor_id": "nc1", "session_id": "s_nc", "event_name": "page_view", "page_url": "/brush", "consent_granted": False},
    ]):
        ConversionAttributionEngine.ingest_event(org_id="org_1", domain="perforacare.com", payload=ev, db_path=db)

    rep = ConversionAttributionEngine.compute_funnel_metrics(org_id="org_1", domain="perforacare.com", db_path=db)
    assert rep.eligible_visitors == 3  # excludes bot + non-consented
    assert rep.conversions == 1
    assert rep.reconciled_net_revenue == 1300.0  # 1500 - 200 refund
    assert rep.by_device["mobile"]["eligible_visitors"] == 3
    assert rep.avg_sdk_load_ms == 4.2

    # 6 Behavioral AI Agents
    agents_out = BehavioralAgentSuite.analyze(org_id="org_1", domain="perforacare.com", db_path=db)
    assert agents_out["status"] == "MEASURED"
    assert len(agents_out["agents_executed"]) == 6
    agent_names = {o["agent_name"] for o in agents_out["observations"]}
    assert {"RageClickAgent", "FormAbandonmentAgent", "MobileUxAgent", "ConversionBehaviourAgent"}.issubset(agent_names)
    for obs in agents_out["observations"]:
        assert obs["recording_ref"].startswith("rec:")
        assert obs["denominator_sessions"] > 0

    # Heatmap with non-eye-tracking disclosure & explicit denominator
    hm = HeatmapEngine.build_page_heatmap(org_id="org_1", domain="perforacare.com", page_url="/brush", device_category="mobile", db_path=db)
    assert hm.status == "MEASURED"
    assert hm.denominator_sessions == 3
    assert "NOT eye-tracking" in hm.movement_concentration_label
    assert len(hm.scroll_insights) == 1
    assert "2/3 sessions" in hm.scroll_insights[0]

    # Replay connectors fail closed when unconfigured (Zero-Fake Policy)
    assert PostHogReplayConnector(api_key=None, project_id=None).fetch_recordings().status == "NOT_CONNECTED"
    assert MicrosoftClarityConnector(api_token=None, project_id=None).fetch_behavioral_insights().status == "NOT_CONNECTED"
