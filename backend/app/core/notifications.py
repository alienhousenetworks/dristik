"""
Email delivery for radar regressions and outcome jobs.

If SMTP is not configured the result is delivery_status=not_configured.
This module never pretends a message was sent.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def notify(
    *,
    subject: str,
    body: str,
    to_email: Optional[str] = None,
    event: str = "notice",
) -> dict:
    recipient = (to_email or settings.NOTIFY_EMAIL or "").strip()
    host = (settings.SMTP_HOST or "").strip()
    sender = (settings.SMTP_FROM or settings.SMTP_USERNAME or "").strip()
    if not host or not sender or not recipient:
        return {
            "event": event,
            "delivery_status": "not_configured",
            "detail": "Set SMTP_HOST, SMTP_FROM, and NOTIFY_EMAIL to send this notice.",
        }
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)
    try:
        with smtplib.SMTP(host, int(settings.SMTP_PORT or 587), timeout=15) as smtp:
            smtp.ehlo()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.starttls()
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception as exc:
        logger.warning("Notification %s failed: %s", event, exc)
        return {"event": event, "delivery_status": "failed", "detail": str(exc)}
    return {"event": event, "delivery_status": "sent", "detail": recipient}
