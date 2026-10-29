"""Razorpay order signature.

Checkout still lives on the payments route. Signature bytes are produced here
so the route and tests share one HMAC.
"""
import hashlib
import hmac

ORDERS_URL = "https://api.razorpay.com/v1/orders"


def payment_signature(secret: str, order_id: str, payment_id: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
