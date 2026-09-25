"""
Dristik AI Content Trust Boundary & Prompt-Injection Firewall
Enforces strict provenance classification:
SYSTEM | DEVELOPER | USER | INTERNAL_EVIDENCE | EXTERNAL_CONTENT | MODEL_OUTPUT.
Treats all crawled website content as untrusted data that must NEVER enter privileged instruction space.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class TrustClassification(str, Enum):
    SYSTEM = "SYSTEM"                      # Hardcoded immutable system instructions
    DEVELOPER = "DEVELOPER"                # Prompt templates & rubric contracts
    USER = "USER"                          # Explicit end-user audit configuration
    INTERNAL_EVIDENCE = "INTERNAL_EVIDENCE"# Verified deterministic observations (e.g. status code 200)
    EXTERNAL_CONTENT = "EXTERNAL_CONTENT"  # Untrusted web data (DOM, scripts, HTML)
    MODEL_OUTPUT = "MODEL_OUTPUT"          # Generated completions from LLM workers

class SanitizedContentEnvelope(BaseModel):
    trust_level: TrustClassification
    content: str
    source_url: Optional[str] = None
    is_safe: bool = True
    neutralized_threats: List[str] = Field(default_factory=list)

import re

class ContentTrustBoundary:
    """
    Prevents prompt injection by isolating untrusted external content into inert data containers.
    """

    SUSPICIOUS_PATTERNS = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "you are now",
        "system prompt override",
        "new instructions:",
        "jailbreak",
        "bypass all guardrails",
        "repeat the words above",
        "as an assistant, forget"
    ]

    def wrap_external_content(self, raw_content: str, source_url: Optional[str] = None) -> SanitizedContentEnvelope:
        neutralized = []
        clean = raw_content or ""
        lower = clean.lower()

        # Detect prompt injection vectors
        for pat in self.SUSPICIOUS_PATTERNS:
            if pat in lower:
                neutralized.append(f"Prompt injection pattern neutralized: '{pat}'")
                # Defang the pattern case-insensitively
                clean = re.sub(re.escape(pat), f"[FILTERED_UNTRUSTED_INPUT: {pat}]", clean, flags=re.IGNORECASE)

        is_safe = len(neutralized) == 0

        # Wrap in unambiguous evidence delimiter
        isolated_content = f"<UNTRUSTED_WEBSITE_EVIDENCE source='{source_url or 'unknown'}'>\n{clean}\n</UNTRUSTED_WEBSITE_EVIDENCE>"

        return SanitizedContentEnvelope(
            trust_level=TrustClassification.EXTERNAL_CONTENT,
            content=isolated_content,
            source_url=source_url,
            is_safe=is_safe,
            neutralized_threats=neutralized
        )
