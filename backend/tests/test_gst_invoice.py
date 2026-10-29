"""
Tests for GST Tax Invoice Generator & UPI Payload
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.payments.store import payment_store, OrderRecord

client = TestClient(app)

def test_gst_invoice_generation_intrastate():
    # Save legitimate order record first
    payment_store.save_order(OrderRecord(
        order_id="diagnostic_order_123",
        plan_id="diagnostic",
        plan_name="Diagnostic Deep-Dive",
        amount_inr=4999,
        amount_paise=499900,
        target_url="https://bangalorestartup.in",
        customer_email="rohan@bangalorestartup.in",
        customer_name="Rohan Sharma",
        company_name="Bangalore Tech Pvt Ltd"
    ))

    # Purchase receipt generation - 0% Tax (Section 22 CGST Act Exempt)
    req = {
        "order_id": "diagnostic_order_123",
        "customer_name": "Rohan Sharma",
        "customer_email": "rohan@bangalorestartup.in",
        "company_name": "Bangalore Tech Pvt Ltd",
        "gstin": "29ABCDE1234F1Z5",
        "state_code": "29",
        "address": "Koramangala, Bangalore"
    }
    res = client.post("/api/v1/payments/invoice", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["base_amount_inr"] == 4999
    assert data["cgst_amount_inr"] == 0
    assert data["sgst_amount_inr"] == 0
    assert data["igst_amount_inr"] == 0
    assert data["total_amount_inr"] == 4999

def test_gst_invoice_generation_interstate():
    payment_store.save_order(OrderRecord(
        order_id="diagnostic_order_456",
        plan_id="diagnostic",
        plan_name="Diagnostic Deep-Dive",
        amount_inr=4999,
        amount_paise=499900,
        target_url="https://mumbaisaas.com",
        customer_email="priya@mumbaisaas.com",
        customer_name="Priya Deshmukh",
        company_name="Mumbai SaaS LLP"
    ))

    # Interstate purchase receipt - 0% Tax
    req = {
        "order_id": "diagnostic_order_456",
        "customer_name": "Priya Deshmukh",
        "customer_email": "priya@mumbaisaas.com",
        "company_name": "Mumbai SaaS LLP",
        "gstin": "27ABCDE1234F1Z5",
        "state_code": "27",
        "address": "Bandra Kurla Complex, Mumbai"
    }
    res = client.post("/api/v1/payments/invoice", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["cgst_amount_inr"] == 0
    assert data["sgst_amount_inr"] == 0
    assert data["igst_amount_inr"] == 0
    assert data["total_amount_inr"] == 4999

def test_gst_invoice_nonexistent_order_fails_closed():
    # Nonexistent orders must fail closed with 404 (never invent fake invoice)
    req = {
        "order_id": "nonexistent_order_999",
        "customer_name": "Fake Customer",
        "customer_email": "fake@example.com"
    }
    res = client.post("/api/v1/payments/invoice", json=req)
    assert res.status_code == 404

def test_order_creation_contains_upi_payload(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_PAYMENT_TEST_MOCKS", True)
    order_req = {
        "plan_id": "diagnostic",
        "target_url": "https://example.com",
        "customer_name": "Test User"
    }
    res = client.post("/api/v1/payments/create-order", json=order_req)
    assert res.status_code == 200
    data = res.json()
    assert "upi_intent_url" in data
    assert "upi://pay?pa=dristik@icici" in data["upi_intent_url"]
    assert data["gst_amount_inr"] == 0
    assert data["total_amount_inr"] == 4999
