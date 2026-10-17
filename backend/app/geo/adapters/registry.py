"""
Engine Adapter Registry.
Dynamically resolves and provisions configured live engine adapters from settings and env.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.geo.adapters.base import BaseGeoEngineAdapter
from app.geo.adapters.perplexity import PerplexityAdapter
from app.geo.adapters.openai_search import OpenAISearchAdapter
from app.geo.adapters.gemini import GeminiAdapter
from app.geo.adapters.claude import ClaudeAdapter
from app.geo.adapters.groq import GroqAdapter


def _adapter_from_configured_engine(eng: Dict[str, Any]) -> Optional[BaseGeoEngineAdapter]:
    """Build the live adapter for one engine row from the citation tracker."""
    provider = (eng.get("provider") or "").lower()
    api_key = eng.get("api_key") or ""
    model = eng.get("model") or ""
    eid = eng.get("id") or ""
    name = eng.get("name") or eid
    if provider in ("openrouter", "together"):
        if provider == "openrouter":
            base = "https://openrouter.ai/api/v1"
            headers = {
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", None) or "https://dristik.ai",
                "X-Title": getattr(settings, "OPENROUTER_SITE_NAME", None) or "Dristik AI",
            }
        else:
            base = getattr(settings, "TOGETHER_BASE_URL", None) or "https://api.together.xyz/v1"
            headers = {}
        return OpenAISearchAdapter(
            api_key=api_key,
            model=model,
            base_url=base,
            extra_headers=headers,
            engine_id=eid,
            display_name=name,
        )
    return None


def _configured_live_adapters() -> List[BaseGeoEngineAdapter]:
    """Active engines that share the admin's main OpenRouter or Together key."""
    from app.geo.citations.tracker import get_configured_ai_engines

    adapters: List[BaseGeoEngineAdapter] = []
    for eng in get_configured_ai_engines():
        if not eng.get("active") or not eng.get("api_key"):
            continue
        if (eng.get("provider") or "").lower() not in ("openrouter", "together"):
            continue
        adapter = _adapter_from_configured_engine(eng)
        if adapter and adapter.is_configured():
            adapters.append(adapter)
    return adapters


def get_adapter(engine_id: str) -> Optional[BaseGeoEngineAdapter]:
    """Resolves an adapter by ID with keys from settings/env."""
    eid = engine_id.lower().strip()
    for adapter in _configured_live_adapters():
        if adapter.engine_id == eid:
            return adapter

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
        model = os.environ.get("AI_CITATION_CHATGPT_MODEL") or "openai/gpt-oss-20b"
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
    """Returns live engines. The gateway models win over separate vendor keys."""
    gateway = _configured_live_adapters()
    if gateway:
        return gateway
    all_adapters = [
        get_adapter("chatgpt"),
        get_adapter("gemini"),
        get_adapter("claude"),
        get_adapter("groq"),
    ]
    # Perplexity Sonar is temporarily stopped by default; re-enable via AI_CITATION_PERPLEXITY_ACTIVE=true
    perp_active = os.environ.get("AI_CITATION_PERPLEXITY_ACTIVE", "false").lower() in ("true", "1", "yes")
    if perp_active:
        all_adapters.append(get_adapter("perplexity"))
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
