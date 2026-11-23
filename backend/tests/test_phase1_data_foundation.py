"""Tests for Phase 1: Data Reliability, Cross-System Reconciliation, Backlinks, and AI Referrals."""
from app.analytics.ai_referral_engine import AiReferralEngine, classify_ai_traffic
from app.db.enterprise_intelligence_schema import connect_enterprise_db
from app.governance.data_reliability import (
    DataReliabilityGovernance,
    normalize_currency,
    normalize_timestamp_utc,
)
from app.seo.intelligence.backlink_intelligence import (
    BacklinkIntelligenceEngine,
    normalize_canonical_domain,
)


def test_data_reliability_reconciliation_exposes_discrepancy(tmp_path):
    db = str(tmp_path / "enterprise.db")
    rec = DataReliabilityGovernance.reconcile_sources(
        org_id="org_1",
        domain="perforacare.com",
        metric_name="purchases",
        source_a_name="GA4",
        source_a_value=100,
        source_b_name="Shopify",
        source_b_value=87,
        tolerance_pct=2.0,
        db_path=db,
    )
    assert rec.reconciliation_status == "DISCREPANCY_DETECTED"
    assert rec.discrepancy_delta == -13.0
    assert rec.discrepancy_pct == 13.0
    assert "does not silently overwrite" in rec.explanation

    ts, tz = normalize_timestamp_utc("2026-11-23T11:00:00+05:30")
    assert ts.startswith("2026-11-23T05:30:00")
    assert tz != "UTC"

    amt, rate, cur = normalize_currency(100.0, "USD", "INR", explicit_fx_rate=84.0)
    assert amt == 8400.0 and rate == 84.0 and cur == "INR"

    assert DataReliabilityGovernance.is_out_of_order_event(
        "2026-11-23T05:00:00Z", "2026-11-23T05:15:00Z", late_threshold_seconds=300
    ) is True


def test_backlink_validation_dedup_reconciliation_and_disavow_approval(tmp_path):
    db = str(tmp_path / "enterprise.db")
    assert normalize_canonical_domain("https://WWW.PerforaCare.com/products/") == "perforacare.com"

    # Snapshot 1: includes 1 duplicate, 1 malformed row, 1 toxic row
    snap1 = BacklinkIntelligenceEngine.ingest_provider_snapshot(
        org_id="org_1",
        domain="perforacare.com",
        provider="dataforseo",
        provider_authority_metric_name="dataforseo_rank",
        provider_authority_metric_value=42.0,
        raw_backlinks=[
            {"source_url": "https://healthblog.com/oral-care", "target_url": "https://perforacare.com/", "anchor": "Perfora", "is_dofollow": True, "provider_rank": 65},
            {"source_url": "https://healthblog.com/oral-care", "target_url": "https://perforacare.com/", "anchor": "Perfora", "is_dofollow": True},  # duplicate
            {"source_url": "https://spam-casino-linkfarm.xyz/p", "target_url": "https://perforacare.com/", "anchor": "buy now", "spam_score": 85},
            {"source_url": "x"},  # invalid schema -> quarantined
        ],
        brand_name="Perfora",
        competitor_domains_map={"colgate.in": ["https://dentaljournal.org", "https://healthblog.com"]},
        db_path=db,
    )
    assert snap1.total_backlinks == 2
    assert snap1.schema_validation_errors == 1
    assert snap1.toxic_candidates_pending_review == 1
    assert snap1.provider_authority_metric_name == "dataforseo_rank"
    assert "dentaljournal.org" in snap1.competitor_gap_domains

    # Snapshot 2: toxic link removed -> must reconcile 1 lost link
    snap2 = BacklinkIntelligenceEngine.ingest_provider_snapshot(
        org_id="org_1",
        domain="perforacare.com",
        provider="dataforseo",
        provider_authority_metric_name="dataforseo_rank",
        provider_authority_metric_value=43.0,
        raw_backlinks=[
            {"source_url": "https://healthblog.com/oral-care", "target_url": "https://perforacare.com/", "anchor": "Perfora", "is_dofollow": True},
        ],
        db_path=db,
    )
    assert snap2.lost_backlinks_since_prev == 1

    # Human disavow approval gate
    conn = connect_enterprise_db(db)
    bl_id = conn.execute("SELECT backlink_id FROM backlinks WHERE dristik_toxic_risk_flag = 1").fetchone()["backlink_id"]
    conn.close()
    rev = BacklinkIntelligenceEngine.review_disavow_candidate(
        org_id="org_1", backlink_id=bl_id, approver_id="user_admin", approve=True, db_path=db
    )
    assert rev["status"] == "APPROVED_FOR_DISAVOW"


def test_ai_referral_classification_attribution_and_order_refund_reconciliation(tmp_path):
    db = str(tmp_path / "enterprise.db")
    assert classify_ai_traffic("https://chatgpt.com/")[0] == "ChatGPT"
    assert classify_ai_traffic("https://www.perplexity.ai/search")[0] == "Perplexity"
    assert classify_ai_traffic("https://www.google.com/", landing_page="https://perforacare.com/p#:~:text=brush")[0] == "Google AI Overviews"
    assert classify_ai_traffic(None)[0] is None

    # Record confirmed transaction & partial refund
    conn = connect_enterprise_db(db)
    conn.execute(
        "INSERT INTO transactions (transaction_id, org_id, domain, order_id, source_platform, gross_amount, net_amount, currency, status, transacted_at_utc, reconciled_at_utc) VALUES ('tx1','org_1','perforacare.com','ORD-100','shopify',2000,2000,'INR','CONFIRMED','2026-11-23T01:00:00Z','2026-11-23T01:00:00Z')"
    )
    conn.execute(
        "INSERT INTO transaction_refunds (refund_id, org_id, order_id, source_platform, refund_amount, currency, refunded_at_utc) VALUES ('ref1','org_1','ORD-100','shopify',500,'INR','2026-11-23T02:00:00Z')"
    )
    conn.commit()
    conn.close()

    # Visitor arrives from Perplexity (touchpoint 1), returns via ChatGPT (touchpoint 2), also 1 unknown session
    AiReferralEngine.record_session(
        org_id="org_1", domain="perforacare.com", session_id="s1", visitor_id="v1",
        landing_page="/electric-toothbrush", http_referrer="https://perplexity.ai/",
        started_at_utc="2026-11-23T01:00:00Z", db_path=db,
    )
    AiReferralEngine.record_session(
        org_id="org_1", domain="perforacare.com", session_id="s2", visitor_id="v1",
        landing_page="/checkout", http_referrer="https://chatgpt.com/", is_new_visitor=False,
        started_at_utc="2026-11-23T01:30:00Z", db_path=db,
    )
    AiReferralEngine.record_session(
        org_id="org_1", domain="perforacare.com", session_id="s3", visitor_id="v2",
        landing_page="/", http_referrer=None, started_at_utc="2026-11-23T01:40:00Z", db_path=db,
    )

    conv = AiReferralEngine.record_conversion_and_attribute(
        org_id="org_1", domain="perforacare.com", event_id="ev_ord_100", visitor_id="v1",
        session_id="s2", event_name="purchase", order_id="ORD-100", monetary_value=2000,
        currency="INR", db_path=db,
    )
    # Reconciled net revenue = 2000 - 500 refund = 1500
    assert conv["reconciled_with_order"] is True
    assert conv["effective_revenue"] == 1500.0

    # Duplicate purchase event must be deduplicated
    dup = AiReferralEngine.record_conversion_and_attribute(
        org_id="org_1", domain="perforacare.com", event_id="ev_ord_100", visitor_id="v1",
        session_id="s2", event_name="purchase", order_id="ORD-100", monetary_value=2000,
        currency="INR", db_path=db,
    )
    assert dup["deduplicated"] is True

    dash = AiReferralEngine.get_dashboard_summary(org_id="org_1", domain="perforacare.com", model_name="last_touch", db_path=db)
    assert dash.ai_referred_sessions == 2
    assert dash.unknown_or_unobservable_sessions == 1
    assert dash.ai_attributed_conversions == 1
    assert dash.ai_assisted_conversions == 1
    assert dash.ai_attributed_revenue == 1500.0
