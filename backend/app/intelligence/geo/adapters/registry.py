"""
Engine Adapter Registry.
Dynamically resolves and provisions configured live engine adapters from settings and env.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional
from app.core.config import settings
from app.intelligence.geo.adapters.base import BaseGeoEngineAdapter
from app.intelligence.geo.adapters.perplexity import PerplexityAdapter
from app.intelligence.geo.adapters.openai_search import OpenAISearchAdapter
from app.intelligence.geo.adapters.gemini import GeminiAdapter
from app.intelligence.geo.adapters.claude import ClaudeAdapter
from app.intelligence.geo.adapters.groq import GroqAdapter


def get_adapter(engine_id: str) -> Optional[BaseGeoEngineAdapter]:
    """Resolves an adapter by ID with keys from settings/env."""
    eid = engine_id.lower().strip()

    if eid in ["perplexity", "sonar"]:
        key = (
            os.environ.get("AI_CITATION_PERPLEXITY_API_KEY")
            or os.environ.get("PERPLEXITY_API_KEY")
            or getattr(settings, "PERPLEXITY_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_PERPLEXITY_MODEL") or "sonar"
        return PerplexityAdapter(api_key=key, model=model)

    elif eid in ["chatgpt", "openai"]:
        key = (
            os.environ.get("AI_CITATION_CHATGPT_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or getattr(settings, "OPENAI_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_CHATGPT_MODEL") or "gpt-4o-mini"
        return OpenAISearchAdapter(api_key=key, model=model)

    elif eid in ["gemini", "google"]:
        key = (
            os.environ.get("AI_CITATION_GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or getattr(settings, "GEMINI_API_KEY", "")
            or getattr(settings, "GOOGLE_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_GEMINI_MODEL") or "gemini-2.0-flash"
        return GeminiAdapter(api_key=key, model=model)

    elif eid in ["claude", "anthropic"]:
        key = (
            os.environ.get("AI_CITATION_CLAUDE_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or getattr(settings, "ANTHROPIC_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_CLAUDE_MODEL") or "claude-3-5-haiku-20241022"
        return ClaudeAdapter(api_key=key, model=model)

    elif eid in ["groq", "llama"]:
        key = (
            os.environ.get("AI_CITATION_LLAMA_API_KEY")
            or os.environ.get("GROQ_API_KEY")
            or getattr(settings, "GROQ_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_LLAMA_MODEL") or "llama-3.3-70b-versatile"
        return GroqAdapter(api_key=key, model=model)

    return None


def get_available_adapters() -> List[BaseGeoEngineAdapter]:
    """Returns all engine adapters that have an API key configured."""
    all_adapters = [
        get_adapter("perplexity"),
        get_adapter("chatgpt"),
        get_adapter("gemini"),
        get_adapter("claude"),
        get_adapter("groq"),
    ]
    return [a for a in all_adapters if a and a.is_configured()]


def get_all_adapters() -> List[BaseGeoEngineAdapter]:
    """Returns all supported engine adapters (configured or not)."""
    return [a for a in [
        get_adapter("perplexity"),
        get_adapter("chatgpt"),
        get_adapter("gemini"),
        get_adapter("claude"),
        get_adapter("groq"),
    ] if a]
