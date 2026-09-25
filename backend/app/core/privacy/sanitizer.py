"""
Dristik AI Untrusted Web Input Sandbox & PII/Secret Redactor (Plane 0)
Treats all public web crawl data as hostile untrusted input.
Scans for prompt injection attacks, secrets, API keys, and PII before passing to LLMs or graph storage.
"""
import re
import hashlib
from typing import Tuple, List, Dict
from app.domain.models import UntrustedObservation

# High-risk prompt injection patterns found in adversarial web pages
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(in\s+developer\s+mode|dan|unrestricted)", re.IGNORECASE),
    re.compile(r"(system\s+prompt|developer\s+override|jailbreak):", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?system\s+directive", re.IGNORECASE),
    re.compile(r"output\s+the\s+system\s+api\s+keys", re.IGNORECASE),
    re.compile(r"begin\s+untrusted\s+instruction\s+execution", re.IGNORECASE)
]

# Sensitive Secret / API Key / PII Patterns
SECRET_PATTERNS = {
    "api_key_openai": re.compile(r"sk-[a-zA-Z0-9]{20,48}"),
    "api_key_github": re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    "api_key_razorpay": re.compile(r"rzp_(test|live)_[a-zA-Z0-9]{14,20}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
}

class ContentSanitizer:
    """Sanitizes raw untrusted crawled content and wraps it in a secure observation envelope."""

    @staticmethod
    def sanitize_untrusted_text(
        raw_text: str,
        source_url: str,
        observation_type: str = "dom_text"
    ) -> Tuple[UntrustedObservation, str]:
        """
        Scans and redacts PII/secrets, detects prompt injection attempts,
        and returns a wrapped UntrustedObservation.
        """
        if not raw_text:
            return UntrustedObservation(
                id=hashlib.sha256(b"").hexdigest()[:16],
                source_url=source_url,
                content_sha256=hashlib.sha256(b"").hexdigest(),
                observation_type=observation_type,
                sanitized_content=""
            ), ""

        content_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        sanitized = raw_text
        redacted_fields: List[str] = []
        has_pii = False
        has_injection = False

        # 1. Detect prompt injection
        for pattern in PROMPT_INJECTION_PATTERNS:
            if pattern.search(sanitized):
                has_injection = True
                sanitized = pattern.sub("[REDACTED_PROMPT_INJECTION_VECTOR]", sanitized)

        # 2. Redact PII and Secrets
        for field_name, regex in SECRET_PATTERNS.items():
            if regex.search(sanitized):
                has_pii = True
                redacted_fields.append(field_name)
                sanitized = regex.sub(f"[REDACTED_{field_name.upper()}]", sanitized)

        # 3. Create typed untrusted observation envelope
        observation = UntrustedObservation(
            id=f"obs_{content_sha256[:12]}",
            source_url=source_url,
            content_sha256=content_sha256,
            observation_type=observation_type,
            sanitized_content=sanitized,
            has_pii=has_pii,
            has_injection_vector=has_injection,
            redacted_fields=redacted_fields,
            is_untrusted_web_input=True
        )

        # 4. Formatted bounded string for prompts
        prompt_safe_envelope = (
            f"```UNTRUSTED_OBSERVATION\n"
            f"Source-URL: {source_url}\n"
            f"Observation-Type: {observation_type}\n"
            f"Integrity-SHA256: {content_sha256}\n"
            f"Content:\n{sanitized}\n"
            f"```"
        )

        return observation, prompt_safe_envelope

content_sanitizer = ContentSanitizer()
