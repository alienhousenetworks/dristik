"""Stripe is not a Dristik checkout.

Stripe Connect credentials, when present, belong to the OAuth connector.
Charging a card through Stripe is not implemented.
"""
from app.core.config import settings


def stripe_checkout_available() -> bool:
    return False


def stripe_oauth_configured() -> bool:
    return bool(settings.STRIPE_CLIENT_ID and settings.STRIPE_CLIENT_SECRET)
