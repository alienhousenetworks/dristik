"""Engine Adapter Registry.

Dynamically resolves and provisions configured live engine adapters from
settings, environment variables, and per-tenant encrypted provider connections,
and builds the dynamic provider capability matrix.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.geo.adapters.base import BaseGeoEngineAdapter
from app.geo.adapters.claude import ClaudeAdapter
from app.geo.adapters.copilot import CopilotAdapter
from app.geo.adapters.deepseek import DeepSeekAdapter
from app.geo.adapters.gemini import GeminiAdapter
from app.geo.adapters.grok import GrokAdapter
from app.geo.adapters.groq import GroqAdapter
from app.geo.adapters.openai_search import OpenAISearchAdapter
from app.geo.adapters.perplexity import PerplexityAdapter


def _adapter_from_configured_engine(eng: Dict[str, Any]) -> Optional[BaseGeoEngineAdapter]:
    provider = (eng.get("provider") or "").lower()
    api_key = eng.get("api_key") or ""
    model = eng.get("model") or ""
    eid = eng.get("id") or ""
    name = eng.get("name") or eid
    if provider in ("openrouter", "together", "togetherapi", "nvidia", "nvidiaapi", "nim"):
        if provider == "openrouter":
            base = "https://openrouter.ai/api/v1"
            headers = {
                "HTTP-Referer": getattr(settings, "OPENROUTER_SITE_URL", None) or "https://dristik.ai",
                "X-Title": getattr(settings, "OPENROUTER_SITE_NAME", None) or "Dristik AI",
            }
        elif provider in ("nvidia", "nvidiaapi", "nim"):
            base = getattr(settings, "NVIDIA_BASE_URL", None) or "https://integrate.api.nvidia.com/v1"
            headers = {}
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
    from app.geo.citations.tracker import get_configured_ai_engines

    adapters: List[BaseGeoEngineAdapter] = []
    for eng in get_configured_ai_engines():
        if not eng.get("active") or not eng.get("api_key"):
            continue
        if (eng.get("provider") or "").lower() not in ("openrouter", "together", "togetherapi", "nvidia", "nvidiaapi", "nim"):
            continue
        adapter = _adapter_from_configured_engine(eng)
        if adapter and adapter.is_configured():
            adapters.append(adapter)
    return adapters


def build_adapter_with_secret(
    engine_id: str,
    api_key: str = "",
    model: str = "",
    endpoint_url: str = "",
) -> Optional[BaseGeoEngineAdapter]:
    eid = engine_id.lower().strip()
    if eid in ("perplexity", "sonar"):
        return PerplexityAdapter(api_key=api_key, model=model or "sonar")
    if eid in ("chatgpt", "openai"):
        return OpenAISearchAdapter(api_key=api_key, model=model or "gpt-4o-mini")
    if eid in ("gemini", "google"):
        return GeminiAdapter(api_key=api_key, model=model or "gemini-2.0-flash")
    if eid in ("claude", "anthropic"):
        return ClaudeAdapter(api_key=api_key, model=model or "claude-3-5-haiku-20241022")
    if eid in ("grok", "xai"):
        return GrokAdapter(api_key=api_key, model=model or "grok-2-latest")
    if eid == "deepseek":
        return DeepSeekAdapter(api_key=api_key, model=model or "deepseek-chat")
    if eid in ("copilot", "microsoft_copilot"):
        return CopilotAdapter(api_key=api_key, model=model or "copilot-enterprise", endpoint_url=endpoint_url)
    if eid in ("groq", "llama"):
        return GroqAdapter(api_key=api_key, model=model or "llama-3.3-70b-versatile")
    return None


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

    if eid in ["chatgpt", "openai"]:
        key = (
            os.environ.get("AI_CITATION_CHATGPT_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or getattr(settings, "OPENAI_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_CHATGPT_MODEL") or "openai/gpt-oss-20b"
        return OpenAISearchAdapter(api_key=key, model=model)

    if eid in ["gemini", "google"]:
        key = (
            os.environ.get("AI_CITATION_GEMINI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or getattr(settings, "GEMINI_API_KEY", "")
            or getattr(settings, "GOOGLE_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_GEMINI_MODEL") or "gemini-2.0-flash"
        return GeminiAdapter(api_key=key, model=model)

    if eid in ["claude", "anthropic"]:
        key = (
            os.environ.get("AI_CITATION_CLAUDE_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or getattr(settings, "ANTHROPIC_API_KEY", "")
            or ""
        )
        model = os.environ.get("AI_CITATION_CLAUDE_MODEL") or "claude-3-5-haiku-20241022"
        return ClaudeAdapter(api_key=key, model=model)

    if eid in ["grok", "xai"]:
        key = os.environ.get("XAI_API_KEY") or getattr(settings, "XAI_API_KEY", "") or ""
        model = os.environ.get("AI_CITATION_GROK_MODEL") or "grok-2-latest"
        return GrokAdapter(api_key=key, model=model)

    if eid == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY") or getattr(settings, "DEEPSEEK_API_KEY", "") or ""
        model = os.environ.get("AI_CITATION_DEEPSEEK_MODEL") or "deepseek-chat"
        return DeepSeekAdapter(api_key=key, model=model)

    if eid in ["copilot", "microsoft_copilot"]:
        key = os.environ.get("COPILOT_API_KEY") or ""
        endpoint = os.environ.get("COPILOT_ENDPOINT_URL") or ""
        return CopilotAdapter(api_key=key, endpoint_url=endpoint)

    if eid in ["groq", "llama"]:
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
    """Returns configured live adapters."""
    gateway = _configured_live_adapters()
    if gateway:
        return gateway
    all_adapters = [
        get_adapter("chatgpt"),
        get_adapter("gemini"),
        get_adapter("claude"),
        get_adapter("grok"),
        get_adapter("deepseek"),
        get_adapter("copilot"),
        get_adapter("groq"),
    ]
    perp_active = os.environ.get("AI_CITATION_PERPLEXITY_ACTIVE", "false").lower() in ("true", "1", "yes")
    if perp_active or os.environ.get("PERPLEXITY_API_KEY"):
        all_adapters.append(get_adapter("perplexity"))
    return [a for a in all_adapters if a and a.is_configured()]


def get_all_adapters() -> List[BaseGeoEngineAdapter]:
    """Returns all supported engine adapters (configured or not)."""
    return [
        a
        for a in [
            get_adapter("chatgpt"),
            get_adapter("gemini"),
            get_adapter("claude"),
            get_adapter("perplexity"),
            get_adapter("grok"),
            get_adapter("copilot"),
            get_adapter("deepseek"),
            get_adapter("groq"),
        ]
        if a
    ]


def get_provider_capability_matrix() -> List[Dict[str, Any]]:
    """Dynamically assemble the provider capability matrix from adapter declarations."""
    return [adapter.get_capabilities().model_dump() for adapter in get_all_adapters()]
