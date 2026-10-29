import pytest
import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_payments_config_endpoint():
    response = client.get("/api/v1/payments/config")
    assert response.status_code == 200
    data = response.json()
    assert "razorpay_key_id" in data
    assert "currency" in data
    assert data["currency"] == "INR"
    assert data["brand_name"] == "Dristik AI"

def test_payments_plans_catalog():
    response = client.get("/api/v1/payments/plans")
    assert response.status_code == 200
    data = response.json()
    assert "one_time_audits" in data
    assert "continuous_monitoring" in data
    
    # Verify pricing catalog
    plans = {p["id"]: p for p in data["one_time_audits"]}
    assert "free_scan" in plans
    assert "starter" in plans
    assert "professional" in plans
    assert "business" in plans
    assert "enterprise" in plans
    
    assert plans["free_scan"]["price_inr"] == 0
    assert plans["starter"]["price_inr"] == 1499
    assert plans["professional"]["price_inr"] == 3499
    assert plans["business"]["price_inr"] == 9999
    assert plans["enterprise"]["price_inr"] == 49999

def test_create_order_fails_closed_without_credentials_or_test_mode(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PAYMENT_TEST_MOCKS", False)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "")
    order_req = {
        "plan_id": "professional",
        "target_url": "https://supabase.com",
        "customer_name": "Test Founder",
        "customer_email": "founder@supabase.com"
    }
    order_res = client.post("/api/v1/payments/create-order", json=order_req)
    assert order_res.status_code == 503

def test_verify_payment_rejects_unauthorized_signature(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PAYMENT_TEST_MOCKS", False)
    verify_req = {
        "razorpay_order_id": "order_fake_123",
        "razorpay_payment_id": "pay_fake_456",
        "razorpay_signature": "mock_sig_invalid",
        "plan_id": "professional",
        "target_url": "https://supabase.com",
        "customer_email": "founder@supabase.com"
    }
    verify_res = client.post("/api/v1/payments/verify-payment", json=verify_req)
    assert verify_res.status_code == 400

def test_create_order_and_verify_flow_with_test_mocks(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PAYMENT_TEST_MOCKS", True)

    # 1. Create order
    order_req = {
        "plan_id": "professional",
        "target_url": "https://supabase.com",
        "customer_name": "Test Founder",
        "customer_email": "founder@supabase.com",
        "company_name": "Supabase Inc."
    }
    order_res = client.post("/api/v1/payments/create-order", json=order_req)
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert order_data["plan_id"] == "professional"
    assert order_data["amount_inr"] == 3499
    assert order_data["gst_amount_inr"] == 0
    assert order_data["total_amount_inr"] == 3499
    assert "order_id" in order_data

    # 2. Verify payment & voucher generation
    verify_req = {
        "razorpay_order_id": order_data["order_id"],
        "razorpay_payment_id": "pay_test_99881122",
        "razorpay_signature": "mock_sig_valid123",
        "plan_id": "professional",
        "target_url": "https://supabase.com",
        "customer_email": "founder@supabase.com"
    }
    verify_res = client.post("/api/v1/payments/verify-payment", json=verify_req)
    assert verify_res.status_code == 200
    voucher_data = verify_res.json()
    assert voucher_data["success"] is True
    assert voucher_data["voucher_code"].startswith("DRISTIK-PROFESSIONAL-")
    assert voucher_data["plan_id"] == "professional"
    assert voucher_data["target_url"] == "https://supabase.com"


def test_post_analysis_voucher_entitlement_enforcement(monkeypatch):
    """Verifies that POST /analyses strictly validates voucher domain binding and authenticity."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "TOGETHER_API_KEY", "mock_key")

    # Sign up an authenticated user with valid password and unique email
    import uuid
    uid = uuid.uuid4().hex[:6]
    signup_res = client.post("/api/v1/auth/signup", json={
        "full_name": "Voucher Test User",
        "email": f"voucher_{uid}@supabase.com",
        "password": "OwnerPass1!",
        "organization_name": "Supabase Test Org",
    })
    assert signup_res.status_code == 200, signup_res.text
    assert "token" not in signup_res.json()

    # 1. Non-existent voucher must return 403 Forbidden
    resp_fake = client.post(
        "/api/v1/analyses",
        json={"website_url": "https://supabase.com", "voucher_code": "DRISTIK-FAKE-12345", "max_crawl_pages": 5},
    )
    assert resp_fake.status_code == 403
    assert "ENTITLEMENT_VIOLATION" in resp_fake.json()["detail"]

    # 2. Create a legitimate voucher bound to https://supabase.com
    from app.payments.store import get_payment_store
    store = get_payment_store()
    voucher = store.issue_voucher(
        order_id="order_test_entitle",
        plan_id="professional",
        target_url="https://supabase.com",
        payment_id="pay_test_entitle",
        max_pages=10
    )

    # 3. Attempt to use voucher on mismatched domain (https://attacker.com) must return 403 Forbidden
    resp_mismatch = client.post(
        "/api/v1/analyses",
        json={"website_url": "https://attacker.com", "voucher_code": voucher.voucher_code, "max_crawl_pages": 5},
    )
    assert resp_mismatch.status_code == 403
    assert "ENTITLEMENT_VIOLATION" in resp_mismatch.json()["detail"]
