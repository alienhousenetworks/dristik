"""
Compatibility re-export from app.commercial.payments.
Billing, Stripe, Razorpay, and subscription management are consolidated into backend/app/commercial/payments/.
"""
from __future__ import annotations

import sys
from app.commercial.payments import (
    gst_billing,
    razorpay,
    service,
    store,
    stripe,
    subscriptions,
)

__path__: list[str] = []

sys.modules["app.payments.gst_billing"] = gst_billing
sys.modules["app.payments.razorpay"] = razorpay
sys.modules["app.payments.service"] = service
sys.modules["app.payments.store"] = store
sys.modules["app.payments.stripe"] = stripe
sys.modules["app.payments.subscriptions"] = subscriptions

__all__ = [
    "gst_billing",
    "razorpay",
    "service",
    "store",
    "stripe",
    "subscriptions",
]
