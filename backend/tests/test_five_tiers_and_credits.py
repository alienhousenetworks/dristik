"""
Comprehensive tests for the 5-Tier Pricing, Credit Wallet/Ledger, All-In COGS,
BudgetManager Tier Scaling, Razorpay Credit Pack Purchase, and Pipeline Feature Gating.
"""
from __future__ import annotations

import os
import tempfile
import pytest

from app.domain.commercial.tiers import (
    AUDIT_TIERS,
    CREDIT_PACKS,
    AuditTierId,
    estimate_audit_quote,
    get_credit_pack,
    get_tier_spec,
    is_feature_enabled,
    list_serialized_tiers,
    normalize_tier_id,
    recommend_pack_for_shortfall,
    specialist_allowed_for_tier,
)
from app.core.inference.budget_manager import BudgetManager
from app.identity.store import IdentityStore


def test_five_tiers_catalog_and_10_page_credit_math():
    """Verify all 5 tiers exist, are strictly ordered, and match the 10-page credit formula."""
    tiers = list_serialized_tiers()
    assert [t["id"] for t in tiers] == ["basic", "starter", "growth", "premium", "enterprise"]

    # 10 pages on Basic = 5 + 10*1 = 15 credits (₹150), zero AI specialists
    q_basic = estimate_audit_quote("basic", 10)
    assert q_basic["required_credits"] == 15
    assert q_basic["price_inr_est"] == 150
    assert q_basic["features"]["specialist_limit"] == 0
    assert q_basic["features"]["aeo_question_count"] == 0
    assert q_basic["features"]["enable_ga4_gsc"] is False
    assert q_basic["features"]["enable_patch_pack_download"] is False

    # 10 pages on Starter = 15 + 10*2 = 35 credits (₹350), 10 specialists
    q_starter = estimate_audit_quote("starter", 10)
    assert q_starter["required_credits"] == 35
    assert q_starter["price_inr_est"] == 350
    assert q_starter["features"]["specialist_limit"] == 10

    # 10 pages on Growth = 30 + 10*4 = 70 credits (₹700), 20 specialists + GA4/GSC + 25-Q AEO
    q_growth = estimate_audit_quote("growth", 10)
    assert q_growth["required_credits"] == 70
    assert q_growth["features"]["specialist_limit"] == 20
    assert q_growth["features"]["aeo_question_count"] == 25
    assert q_growth["features"]["enable_ga4_gsc"] is True
    assert q_growth["features"]["enable_psi_crux"] is False

    # 10 pages on Premium = 50 + 10*6 = 110 credits (₹1,100), ALL 35 specialists + 100-Q AEO + 5 PDF/5 PPT
    q_premium = estimate_audit_quote("premium", 10)
    assert q_premium["required_credits"] == 110
    assert q_premium["price_inr_est"] == 1100
    assert q_premium["features"]["specialist_limit"] == 35
    assert q_premium["features"]["aeo_question_count"] == 100
    assert q_premium["features"]["enable_ga4_gsc"] is True
    assert q_premium["features"]["enable_psi_crux"] is True
    assert q_premium["features"]["enable_patch_pack_download"] is True
    assert q_premium["features"]["report_documents_mode"] == "full_5_5_standard"

    # 10 pages on Enterprise = 90 + 10*10 = 190 credits (₹1,900), frontier_all + Live GEO + Bake-Off + White-Label
    q_ent = estimate_audit_quote("enterprise", 10)
    assert q_ent["required_credits"] == 190
    assert q_ent["price_inr_est"] == 1900
    assert q_ent["features"]["enable_live_geo_probes"] is True
    assert q_ent["features"]["enable_competitor_bakeoff"] is True
    assert q_ent["features"]["white_label_enabled"] is True
    assert q_ent["features"]["ai_depth_mode"] == "frontier_all"

    # All-in COGS includes infra, connectors, AI, live GEO, render, and Razorpay fee, maintaining > 55% margin
    for tid in ("basic", "starter", "growth", "premium", "enterprise"):
        q = estimate_audit_quote(tid, 10)
        cogs = q["cogs_breakdown_inr"]
        assert cogs["total_cogs_inr"] > 0
        assert cogs["payment_gateway_fee_inr"] > 0
        assert q["estimated_gross_margin_pct"] >= 55.0


def test_specialist_and_feature_gating_rules():
    """Basic locks all specialists; Starter unlocks 10; Growth unlocks 20; Premium/Enterprise unlock all 35."""
    assert specialist_allowed_for_tier("basic", "technical_seo_audit", 0) is False
    assert specialist_allowed_for_tier("starter", "technical_seo_audit", 0) is True
    assert specialist_allowed_for_tier("starter", "random_extra_agent", 25) is False
    assert specialist_allowed_for_tier("growth", "direct_answer_audit", 15) is True
    assert specialist_allowed_for_tier("growth", "random_extra_agent", 30) is False
    assert specialist_allowed_for_tier("premium", "random_extra_agent", 34) is True
    assert specialist_allowed_for_tier("enterprise", "random_extra_agent", 34) is True

    assert is_feature_enabled("basic", "enable_patch_pack_download") is False
    assert is_feature_enabled("premium", "enable_patch_pack_download") is True
    assert is_feature_enabled("premium", "enable_competitor_bakeoff") is False
    assert is_feature_enabled("enterprise", "enable_competitor_bakeoff") is True

    # Legacy alias normalization
    assert normalize_tier_id("free_scan") == "basic"
    assert normalize_tier_id("diagnostic") == "premium"
    assert normalize_tier_id("diagnostic_bakeoff") == "enterprise"


def test_budget_manager_scales_by_tier_and_fixes_80_call_cap():
    """BudgetManager gives Basic 0 calls, Starter/Growth bounded calls, and Premium/Enterprise >= 140/180 calls."""
    b_basic = BudgetManager.compute_audit_budget(10, tier_id="basic")
    assert b_basic.max_budget_usd == 0.0
    assert b_basic.max_model_calls == 0

    b_starter = BudgetManager.compute_audit_budget(10, tier_id="starter")
    assert 20 <= b_starter.max_model_calls <= 40

    b_growth = BudgetManager.compute_audit_budget(10, tier_id="growth")
    assert b_growth.max_model_calls >= 65

    b_prem = BudgetManager.compute_audit_budget(15, tier_id="premium")
    assert b_prem.max_model_calls >= 140  # Previously capped at 80 and dropped specialists!

    b_ent = BudgetManager.compute_audit_budget(15, tier_id="enterprise")
    assert b_ent.max_model_calls >= 180
    assert b_ent.max_budget_usd > b_prem.max_budget_usd


def test_identity_store_atomic_credit_wallet_debit_refund_and_idempotency():
    """Verify persistent SQLite credit wallet: signup bonus, atomic debit, rejection on shortfall, idempotent refund/purchase."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_credits.db")
        store = IdentityStore(db_path)
        try:
            org = store.create_organization("Acme Corp", "acme-corp")
            org_id = org["org_id"]
            # Default 20 starter credits
            assert store.get_credit_balance(org_id) == 20

            # 10-page Basic costs 15 credits -> succeeds, leaves 5
            ok, bal = store.debit_credits(
                org_id,
                15,
                reference_id="run_basic_1",
                audit_tier="basic",
                pages_count=10,
                note="Basic 10p",
            )
            assert ok is True
            assert bal == 5
            assert store.get_credit_balance(org_id) == 5

            # 10-page Premium costs 110 credits -> rejected, balance unchanged
            ok2, bal2 = store.debit_credits(
                org_id,
                110,
                reference_id="run_prem_1",
                audit_tier="premium",
                pages_count=10,
            )
            assert ok2 is False
            assert bal2 == 5
            assert store.get_credit_balance(org_id) == 5

            # Purchase pack_150 (+150 credits) -> idempotent on payment_id
            bal3 = store.add_credits(org_id, 150, entry_type="PURCHASE", reference_id="pay_rzp_123", note="pack_150")
            assert bal3 == 155
            bal3_dup = store.add_credits(org_id, 150, entry_type="PURCHASE", reference_id="pay_rzp_123", note="pack_150")
            assert bal3_dup == 155  # No double-credit

            # Now 10-page Premium succeeds (155 - 110 = 45)
            ok3, bal4 = store.debit_credits(
                org_id,
                110,
                reference_id="run_prem_2",
                audit_tier="premium",
                pages_count=10,
            )
            assert ok3 is True
            assert bal4 == 45

            # Auto-refund on fatal crawl failure (idempotent on analysis_id)
            bal5 = store.add_credits(org_id, 110, entry_type="AUDIT_REFUND", reference_id="run_prem_2", note="Failed crawl")
            assert bal5 == 155
            bal5_dup = store.add_credits(org_id, 110, entry_type="AUDIT_REFUND", reference_id="run_prem_2", note="Failed crawl")
            assert bal5_dup == 155

            ledger = store.list_credit_ledger(org_id)
            entry_types = [e["entry_type"] for e in ledger]
            assert "SIGNUP_BONUS" in entry_types
            assert "AUDIT_DEBIT" in entry_types
            assert "PURCHASE" in entry_types
            assert "AUDIT_REFUND" in entry_types
        finally:
            store.close()


def test_credit_packs_and_shortfall_recommendation():
    assert len(CREDIT_PACKS) == 5
    assert get_credit_pack("pack_150")["credits"] == 150
    assert recommend_pack_for_shortfall(30)["id"] == "pack_50"
    assert recommend_pack_for_shortfall(105)["id"] == "pack_150"
    assert recommend_pack_for_shortfall(450)["id"] == "pack_500"
