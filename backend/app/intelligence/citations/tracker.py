"""
Dristik AI Real AI Citation Tracker (Hero Feature)
Monitors real commercial buyer queries across the top 8 AI Answer Engines.
Fails closed with an exact reason and a next step — never a silent spinner.
"""
import os
import re
import asyncio
import httpx
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.core.config import settings, Settings, ANTHROPIC_DEFAULT_FAST, GROQ_DEFAULT_REASONING
from app.orchestration.orchestrator import orchestrator

ENGINE_TIMEOUT_SECONDS = 8.0
DASHBOARD_TIMEOUT_SECONDS = 45.0


class EngineQueryResult(BaseModel):
    engine: str
    was_mentioned: bool
    position: Optional[int] = None
    was_cited: bool
    cited_url: Optional[str] = None
    competitor_cited_instead: Optional[str] = None
    source_domains_used: List[str] = Field(default_factory=list)
    synthesized_snippet: str
    extractability_health: str
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None


class RealBuyerQueryEvaluation(BaseModel):
    query_id: str
    buyer_query: str
    commercial_intent: str
    monthly_search_volume: Optional[int] = None
    engines: List[EngineQueryResult] = Field(default_factory=list)
    overall_citation_status: str
    primary_competitor_capturing: str
    recommended_action: str


class AiCitationTrackingDashboard(BaseModel):
    target_domain: str
    total_queries_tracked: int
    overall_ai_citation_score: Optional[int] = None
    engines_breakdown: Dict[str, float] = Field(default_factory=dict)
    tracked_queries: List[RealBuyerQueryEvaluation] = Field(default_factory=list)
    critical_ai_blindspots: List[str] = Field(default_factory=list)
    is_live: bool = False
    provider_used: Optional[str] = None
    status_message: Optional[str] = None
    engines_measured_count: int = 0
    engines_total_count: int = 8
    failure_reason: Optional[str] = None
    failure_code: Optional[str] = None
    next_steps: List[str] = Field(default_factory=list)
    engine_errors: List[str] = Field(default_factory=list)


def _parse_bool(val: Any, default: bool = True) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "on", "t"):
        return True
    if s in ("0", "false", "no", "off", "f"):
        return False
    return default


def _engine_active(flag_name: str, has_native_key: bool) -> bool:
    """Honor an explicit ACTIVE flag; otherwise enable only when a native key exists."""
    raw = os.environ.get(flag_name)
    if raw is not None and str(raw).strip() != "":
        return _parse_bool(raw, default=False)
    return bool(has_native_key)


def _provider_family(provider: str) -> set:
    p = (provider or "").lower().strip()
    groups = (
        {"anthropic", "claude"},
        {"gemini", "google"},
        {"groq"},
        {"openrouter"},
        {"openai"},
        {"together"},
        {"perplexity"},
        {"deepseek"},
        {"xai", "grok"},
        {"moonshot", "kimi"},
    )
    for group in groups:
        if p in group:
            return group
    return {p} if p else set()


def _engine_matches_active_provider(engine_provider: str) -> bool:
    """
    LLM_PROVIDER is the only live inference vendor unless
    AI_CITATION_CROSS_PROVIDER=true opts into multi-engine fan-out.
    """
    if _parse_bool(os.environ.get("AI_CITATION_CROSS_PROVIDER"), default=False):
        return True
    active = (settings.get_active_provider() or "").lower().strip()
    family = _provider_family(active)
    return (engine_provider or "").lower().strip() in family


def get_configured_ai_engines() -> List[Dict[str, Any]]:
    """
    Builds the AI answer engines list dynamically from environment variables
    and settings, enabling independent keys, models, providers, and active toggles.
    """
    or_key = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or ""

    def _or_key_if(provider: str) -> str:
        return or_key if provider == "openrouter" else ""

    # 1. Google Gemini
    gemini_native = (
        os.environ.get("AI_CITATION_GEMINI_API_KEY")
        or settings.GEMINI_API_KEY
        or os.environ.get("GEMINI_API_KEY")
        or settings.GOOGLE_API_KEY
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    )
    gemini_provider = (os.environ.get("AI_CITATION_GEMINI_PROVIDER") or ("gemini" if gemini_native else "gemini")).lower()
    gemini_key = gemini_native or _or_key_if(gemini_provider)
    gemini_active = _engine_active("AI_CITATION_GEMINI_ACTIVE", bool(gemini_native))
    gemini_model = os.environ.get("AI_CITATION_GEMINI_MODEL") or ("google/gemini-2.0-flash-exp:free" if gemini_provider == "openrouter" else "gemini-2.0-flash")

    # 2. ChatGPT (OpenAI)
    chatgpt_native = (
        os.environ.get("AI_CITATION_CHATGPT_API_KEY")
        or settings.OPENAI_API_KEY
        or os.environ.get("OPENAI_API_KEY")
        or ""
    )
    chatgpt_provider = (os.environ.get("AI_CITATION_CHATGPT_PROVIDER") or ("openai" if chatgpt_native else "openai")).lower()
    chatgpt_key = chatgpt_native or _or_key_if(chatgpt_provider)
    chatgpt_active = _engine_active("AI_CITATION_CHATGPT_ACTIVE", bool(chatgpt_native))
    chatgpt_model = os.environ.get("AI_CITATION_CHATGPT_MODEL") or ("openai/gpt-4o-mini" if chatgpt_provider == "openrouter" else "gpt-4o-mini")

    # 3. Perplexity Pro
    perp_native = (
        os.environ.get("AI_CITATION_PERPLEXITY_API_KEY")
        or os.environ.get("PERPLEXITY_API_KEY")
        or settings.PERPLEXITY_API_KEY
        or ""
    )
    perp_provider = (os.environ.get("AI_CITATION_PERPLEXITY_PROVIDER") or ("perplexity" if perp_native else "perplexity")).lower()
    perp_key = perp_native or _or_key_if(perp_provider)
    perp_active = _engine_active("AI_CITATION_PERPLEXITY_ACTIVE", bool(perp_native))
    perp_model = os.environ.get("AI_CITATION_PERPLEXITY_MODEL") or ("perplexity/sonar" if perp_provider == "openrouter" else "sonar")

    # 4. Claude (Anthropic)
    claude_native = (
        os.environ.get("AI_CITATION_CLAUDE_API_KEY")
        or settings.ANTHROPIC_API_KEY
        or os.environ.get("ANTHROPIC_API_KEY")
        or settings.CLAUDE_API_KEY
        or os.environ.get("CLAUDE_API_KEY")
        or ""
    )
    claude_provider = (os.environ.get("AI_CITATION_CLAUDE_PROVIDER") or ("anthropic" if claude_native else "anthropic")).lower()
    claude_key = claude_native or _or_key_if(claude_provider)
    claude_active = _engine_active("AI_CITATION_CLAUDE_ACTIVE", bool(claude_native))
    raw_claude_model = os.environ.get("AI_CITATION_CLAUDE_MODEL") or settings.ANTHROPIC_MODEL or os.environ.get("ANTHROPIC_MODEL")
    if claude_provider == "openrouter":
        claude_model = raw_claude_model or "anthropic/claude-haiku-4.5"
    else:
        claude_model = Settings._coerce_anthropic_model(raw_claude_model, ANTHROPIC_DEFAULT_FAST)

    # 5. DeepSeek
    deepseek_native = (
        os.environ.get("AI_CITATION_DEEPSEEK_API_KEY")
        or settings.DEEPSEEK_API_KEY
        or os.environ.get("DEEPSEEK_API_KEY")
        or ""
    )
    deepseek_provider = (os.environ.get("AI_CITATION_DEEPSEEK_PROVIDER") or ("deepseek" if deepseek_native else "deepseek")).lower()
    deepseek_key = deepseek_native or _or_key_if(deepseek_provider)
    deepseek_active = _engine_active("AI_CITATION_DEEPSEEK_ACTIVE", bool(deepseek_native))
    deepseek_model = os.environ.get("AI_CITATION_DEEPSEEK_MODEL") or ("deepseek/deepseek-chat" if deepseek_provider == "openrouter" else "deepseek-chat")

    # 6. Kimi (Moonshot AI)
    kimi_key = os.environ.get("AI_CITATION_KIMI_API_KEY") or settings.MOONSHOT_API_KEY or os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY") or ""
    kimi_active = _engine_active("AI_CITATION_KIMI_ACTIVE", bool(kimi_key))
    kimi_provider = (os.environ.get("AI_CITATION_KIMI_PROVIDER") or "moonshot").lower()
    kimi_model = os.environ.get("AI_CITATION_KIMI_MODEL") or "moonshot-v1-8k"

    # 7. xAI Grok
    grok_key = os.environ.get("AI_CITATION_GROK_API_KEY") or settings.XAI_API_KEY or os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY") or ""
    grok_active = _engine_active("AI_CITATION_GROK_ACTIVE", bool(grok_key))
    grok_provider = (os.environ.get("AI_CITATION_GROK_PROVIDER") or "xai").lower()
    grok_model = os.environ.get("AI_CITATION_GROK_MODEL") or "grok-2-latest"

    # 8. Meta Llama — Groq by default when a Groq key exists. Do not fall back to OpenRouter.
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY") or ""
    together_key = settings.TOGETHER_API_KEY or os.environ.get("TOGETHER_API_KEY") or ""
    llama_native = os.environ.get("AI_CITATION_LLAMA_API_KEY") or groq_key or together_key or ""
    llama_provider = (os.environ.get("AI_CITATION_LLAMA_PROVIDER") or ("groq" if groq_key else ("together" if together_key else "groq"))).lower()
    llama_key = llama_native or _or_key_if(llama_provider)
    llama_active = _engine_active("AI_CITATION_LLAMA_ACTIVE", bool(llama_native))
    llama_model = os.environ.get("AI_CITATION_LLAMA_MODEL") or (
        GROQ_DEFAULT_REASONING if llama_provider == "groq"
        else ("meta-llama/Llama-3.3-70B-Instruct-Turbo" if llama_provider == "together" else "meta-llama/llama-3.3-70b-instruct")
    )
    if llama_provider == "groq":
        llama_model = Settings._coerce_groq_model(llama_model, GROQ_DEFAULT_REASONING)

    engines = [
        {"id": "gemini", "name": "Google Gemini", "category": "Knowledge Graph & Multimodal Discovery", "active": gemini_active, "provider": gemini_provider, "api_key": gemini_key, "model": gemini_model},
        {"id": "chatgpt", "name": "ChatGPT (OpenAI)", "category": "Conversational & Search Grounded", "active": chatgpt_active, "provider": chatgpt_provider, "api_key": chatgpt_key, "model": chatgpt_model},
        {"id": "perplexity", "name": "Perplexity Pro", "category": "Live Real-Time Web Search Citations", "active": perp_active, "provider": perp_provider, "api_key": perp_key, "model": perp_model},
        {"id": "claude", "name": "Claude (Anthropic)", "category": "Reasoning & Technical Synthesis", "active": claude_active, "provider": claude_provider, "api_key": claude_key, "model": claude_model},
        {"id": "deepseek", "name": "DeepSeek", "category": "Open Architecture & Algorithmic Discovery", "active": deepseek_active, "provider": deepseek_provider, "api_key": deepseek_key, "model": deepseek_model},
        {"id": "kimi", "name": "Kimi (Moonshot AI)", "category": "Long Context & Document Grounding", "active": kimi_active, "provider": kimi_provider, "api_key": kimi_key, "model": kimi_model},
        {"id": "grok", "name": "xAI Grok", "category": "Real-Time Discovery & Public Signals", "active": grok_active, "provider": grok_provider, "api_key": grok_key, "model": grok_model},
        {"id": "llama", "name": "Meta Llama 3.3", "category": "Enterprise Open Weights Ecosystem", "active": llama_active, "provider": llama_provider, "api_key": llama_key, "model": llama_model},
    ]
    for eng in engines:
        if eng.get("active") and not _engine_matches_active_provider(str(eng.get("provider") or "")):
            eng["active"] = False
    return engines


AI_ENGINES: List[Dict[str, Any]] = get_configured_ai_engines()

NO_KEY_NEXT_STEPS = [
    "Configure ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or PERPLEXITY_API_KEY in backend/.env.",
    "Verify that active engines have valid keys or toggle AI_CITATION_<ENGINE>_ACTIVE=false for unused engines.",
    "Restart the API process after saving the key.",
    "Re-run this tracker. Until an active key is present, citation score stays null (zero-fake standard).",
]


def _snippet_error(status_code: int, body: str) -> str:
    text = (body or "").replace("\n", " ").strip()
    if len(text) > 220:
        text = text[:217] + "..."
    if status_code == 401 or status_code == 403:
        return f"HTTP {status_code} unauthorized. The API key is missing, revoked, or not allowed for this model. {text}"
    if status_code == 402:
        return f"HTTP 402 payment required. The provider account is out of credits. {text}"
    if status_code == 404:
        return f"HTTP 404 model not found. The routed model id is unavailable on this key. {text}"
    if status_code == 429:
        return f"HTTP 429 rate limited. Wait and retry, or switch provider. {text}"
    if status_code >= 500:
        return f"HTTP {status_code} provider outage. {text}"
    if status_code:
        return f"HTTP {status_code}. {text}" if text else f"HTTP {status_code} with empty body."
    return text or "Unknown engine error."


def _unavailable_dashboard(
    target_domain: str,
    provider_used: Optional[str],
    failure_code: str,
    failure_reason: str,
    next_steps: List[str],
    engine_errors: Optional[List[str]] = None,
) -> AiCitationTrackingDashboard:
    return AiCitationTrackingDashboard(
        target_domain=target_domain,
        total_queries_tracked=0,
        overall_ai_citation_score=None,
        engines_breakdown={},
        tracked_queries=[],
        critical_ai_blindspots=[failure_reason],
        is_live=False,
        provider_used=provider_used,
        status_message=failure_reason if failure_reason.startswith("Live AI citation tracking is UNAVAILABLE")
        else f"Live AI citation tracking is UNAVAILABLE. {failure_reason}",
        engines_measured_count=0,
        engines_total_count=len(AI_ENGINES),
        failure_reason=failure_reason,
        failure_code=failure_code,
        next_steps=next_steps,
        engine_errors=engine_errors or [],
    )


class AiCitationTracker:
    """
    Engine that evaluates real citations and competitor substitutions across
    the top AI search & conversational answer engines.
    """

    async def _query_anthropic_live(
        self,
        query: str,
        model: str,
        api_key: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        async def _do_post(c: httpx.AsyncClient) -> Dict[str, Any]:
            try:
                res = await c.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": Settings._coerce_anthropic_model(model, ANTHROPIC_DEFAULT_FAST),
                        "max_tokens": 300,
                        "messages": [
                            {"role": "user", "content": query}
                        ]
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    content_blocks = data.get("content", [])
                    content = "".join(b.get("text", "") for b in content_blocks if isinstance(b, dict) and b.get("type") == "text")
                    return {"content": content, "citations": [], "error": None, "status_code": 200}
                return {
                    "content": "",
                    "citations": [],
                    "error": _snippet_error(res.status_code, res.text),
                    "status_code": res.status_code,
                }
            except httpx.TimeoutException:
                return {"content": "", "citations": [], "error": f"Timeout after {ENGINE_TIMEOUT_SECONDS:.0f}s contacting Anthropic ({model}).", "status_code": 0}
            except Exception as exc:
                return {"content": "", "citations": [], "error": f"Anthropic request failed: {exc}", "status_code": 0}

        if client:
            return await _do_post(client)
        async with httpx.AsyncClient(timeout=ENGINE_TIMEOUT_SECONDS) as local_client:
            return await _do_post(local_client)

    async def _query_perplexity_live(self, query: str, api_key: str, model: str = "sonar") -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=ENGINE_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an objective search engine. Answer factually with real source citations."},
                            {"role": "user", "content": query}
                        ],
                        "max_tokens": 300,
                        "return_citations": True
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    citations = data.get("citations", [])
                    return {"content": content, "citations": citations, "error": None, "status_code": 200}
                return {
                    "content": "",
                    "citations": [],
                    "error": _snippet_error(res.status_code, res.text),
                    "status_code": res.status_code,
                }
        except httpx.TimeoutException:
            return {"content": "", "citations": [], "error": f"Timeout after {ENGINE_TIMEOUT_SECONDS:.0f}s contacting Perplexity.", "status_code": 0}
        except Exception as exc:
            return {"content": "", "citations": [], "error": f"Perplexity request failed: {exc}", "status_code": 0}

    async def _query_openai_compatible_engine(
        self,
        query: str,
        model: str,
        api_key: str,
        base_url: str,
        extra_headers: Optional[Dict[str, str]] = None,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **(extra_headers or {})
        }
        async def _do_post(c: httpx.AsyncClient) -> Dict[str, Any]:
            try:
                res = await c.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": model,
                        "max_tokens": 250,
                        "messages": [
                            {"role": "user", "content": query}
                        ]
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    citations = data.get("citations", [])
                    return {"content": content, "citations": citations, "error": None, "status_code": 200}
                return {
                    "content": "",
                    "citations": [],
                    "error": _snippet_error(res.status_code, res.text),
                    "status_code": res.status_code,
                }
            except httpx.TimeoutException:
                return {
                    "content": "",
                    "citations": [],
                    "error": f"Timeout after {ENGINE_TIMEOUT_SECONDS:.0f}s calling {model}.",
                    "status_code": 0,
                }
            except Exception as exc:
                return {
                    "content": "",
                    "citations": [],
                    "error": f"{model} request failed: {exc}",
                    "status_code": 0,
                }

        if client:
            return await _do_post(client)
        async with httpx.AsyncClient(timeout=ENGINE_TIMEOUT_SECONDS) as local_client:
            return await _do_post(local_client)

    async def _query_openrouter_live(self, query: str, api_key: str) -> Dict[str, Any]:
        return await self._query_openrouter_engine(query, "perplexity/sonar", api_key)

    async def _query_openrouter_engine(
        self,
        query: str,
        model: str,
        api_key: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        return await self._query_openai_compatible_engine(
            query=query,
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            extra_headers={
                "HTTP-Referer": "https://dristik.ai",
                "X-Title": "Dristik AI Live Citation Tracker"
            },
            client=client
        )

    async def _dispatch_engine_call(
        self,
        query: str,
        eng: Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        provider = (eng.get("provider") or "openrouter").lower()
        api_key = eng.get("api_key") or ""
        model = eng.get("model") or ""

        if not api_key:
            return {
                "content": "",
                "citations": [],
                "error": f"Missing API key for {eng.get('name')} (provider: {provider}). Set AI_CITATION_{eng['id'].upper()}_API_KEY in backend/.env.",
                "status_code": 401
            }

        if provider in ["anthropic", "claude"]:
            return await self._query_anthropic_live(query, model, api_key, client)
        elif provider == "perplexity":
            return await self._query_perplexity_live(query, api_key, model=model)
        elif provider == "openai":
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.openai.com/v1", client=client)
        elif provider == "deepseek":
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.deepseek.com", client=client)
        elif provider in ["gemini", "google"]:
            return await self._query_openai_compatible_engine(query, model, api_key, "https://generativelanguage.googleapis.com/v1beta/openai", client=client)
        elif provider == "groq":
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.groq.com/openai/v1", client=client)
        elif provider in ["xai", "grok"]:
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.x.ai/v1", client=client)
        elif provider in ["moonshot", "kimi"]:
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.moonshot.cn/v1", client=client)
        elif provider == "together":
            return await self._query_openai_compatible_engine(query, model, api_key, "https://api.together.xyz/v1", client=client)
        else:
            return await self._query_openrouter_engine(query, model, api_key, client)

    def _evaluate_engine_output(
        self,
        engine_name: str,
        content: str,
        citations: List[str],
        target_domain: str,
        brand: str
    ) -> EngineQueryResult:
        lower_content = (content or "").lower()
        lower_domain = target_domain.lower()
        lower_brand = brand.lower()
        has_mention = bool(lower_brand) and (lower_domain in lower_content or lower_brand in lower_content)

        matched_url = None
        for c in citations:
            c_str = str(c).strip()
            if lower_domain in c_str.lower():
                matched_url = c_str
                break
        if not matched_url and (f"https://{lower_domain}" in lower_content or f"http://{lower_domain}" in lower_content):
            url_match = re.search(rf"https?://[^\s<>'\"]*{re.escape(lower_domain)}[^\s<>'\"]*", content, re.IGNORECASE)
            if url_match:
                matched_url = url_match.group(0)

        has_link = matched_url is not None

        extracted_domains: List[str] = []
        for c in citations:
            match = re.search(r"https?://([^/]+)", str(c))
            if match:
                d = match.group(1).lower()
                if d not in extracted_domains and d != lower_domain:
                    extracted_domains.append(d)

        for match in re.finditer(r"https?://([a-zA-Z0-9\.\-]+)", content or ""):
            d = match.group(1).lower()
            if d not in extracted_domains and d != lower_domain and "openrouter" not in d and "dristik" not in d:
                extracted_domains.append(d)

        competitor_cited: Optional[str] = None
        if not has_link and extracted_domains:
            competitor_cited = extracted_domains[0]
        elif not has_mention:
            comp_match = re.findall(r"(?:alternatives? to|competitors?|such as|like)\s+([A-Z][A-Za-z0-9\s]+)", content or "")
            if comp_match:
                competitor_cited = comp_match[0].strip()

        health = "CITABLE" if has_link else ("MENTIONED_NO_LINK" if has_mention else ("COMPETITOR_DOMINATED" if competitor_cited else "OMITTED"))
        snippet = content[:320] + "..." if content and len(content) > 320 else (content or f"No direct citation captured by {engine_name}.")

        position = None
        if has_mention:
            if re.search(rf"(?:1\.|#1|first|top choice|primary).*?{re.escape(lower_brand)}", lower_content):
                position = 1
            elif re.search(rf"(?:2\.|#2|second).*?{re.escape(lower_brand)}", lower_content):
                position = 2
            elif re.search(rf"(?:3\.|#3|third).*?{re.escape(lower_brand)}", lower_content):
                position = 3

        return EngineQueryResult(
            engine=engine_name,
            was_mentioned=has_mention,
            position=position,
            was_cited=has_link,
            cited_url=matched_url,
            competitor_cited_instead=competitor_cited,
            source_domains_used=extracted_domains[:4],
            synthesized_snippet=snippet,
            extractability_health=health
        )

    def _engine_disabled(self, engine_name: str) -> EngineQueryResult:
        return EngineQueryResult(
            engine=engine_name,
            was_mentioned=False,
            position=None,
            was_cited=False,
            cited_url=None,
            competitor_cited_instead=None,
            source_domains_used=[],
            synthesized_snippet=f"{engine_name} was skipped (inactive in configuration).",
            extractability_health="DISABLED",
            failure_reason=None,
            failure_code="disabled",
        )

    def _engine_unavailable(self, engine_name: str, reason: str, code: Optional[str] = None) -> EngineQueryResult:
        return EngineQueryResult(
            engine=engine_name,
            was_mentioned=False,
            position=None,
            was_cited=False,
            cited_url=None,
            competitor_cited_instead=None,
            source_domains_used=[],
            synthesized_snippet=f"{engine_name} was not measured. {reason}",
            extractability_health="UNAVAILABLE",
            failure_reason=reason,
            failure_code=code,
        )

    async def track_buyer_queries(
        self,
        domain: str = "example.com",
        biz_name: str = "Your Company",
        niche: str = "Software Development",
        analysis_id: Optional[str] = None
    ) -> AiCitationTrackingDashboard:
        target_domain = domain.replace("https://", "").replace("http://", "").split("/")[0]
        brand = biz_name
        industry = niche

        if analysis_id:
            run = orchestrator.get_run(analysis_id)
            if run and run.report:
                target_domain = run.report.domain or target_domain
                if run.report.business_profile:
                    brand = run.report.business_profile.business_name or brand
                    industry = run.report.business_profile.industry or industry

        buyer_queries = [
            {
                "query_id": "Q-01",
                "query": f"What is {brand} ({target_domain}), what does it do, and what are its core features?",
                "intent": "Brand Identity & Capability Discovery",
            },
            {
                "query_id": "Q-02",
                "query": f"How much does {brand} cost, and what are the pricing tiers or implementation fees?",
                "intent": "Price Discovery & Tier Transparency",
            },
            {
                "query_id": "Q-03",
                "query": f"Top alternatives and competitors to {brand} ({target_domain}) for {industry}",
                "intent": "Competitive Bake-Off & Head-to-Head",
            }
        ]

        configured_engines = get_configured_ai_engines()
        active_engines = [e for e in configured_engines if e.get("active", True)]
        
        perp_key = os.environ.get("PERPLEXITY_API_KEY") or settings.PERPLEXITY_API_KEY
        or_key = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY")
        groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
        gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or settings.GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY")
        anthropic_key = settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY") or settings.CLAUDE_API_KEY or os.environ.get("CLAUDE_API_KEY")

        has_keys = bool(
            perp_key or or_key or groq_key or gemini_key or anthropic_key
            or any(bool(e.get("api_key")) for e in active_engines)
        )
        if not has_keys:
            return _unavailable_dashboard(
                target_domain=target_domain,
                provider_used=None,
                failure_code="missing_api_key",
                failure_reason=(
                    "Live AI citation tracking is UNAVAILABLE. Configure ANTHROPIC_API_KEY, GEMINI_API_KEY, "
                    "GROQ_API_KEY, OPENROUTER_API_KEY, or PERPLEXITY_API_KEY in backend/.env to monitor live "
                    "search-grounded citation graphs across active engines."
                ),
                next_steps=NO_KEY_NEXT_STEPS,
            )

        active_providers = sorted(list(set(e.get("provider", "direct") for e in active_engines if e.get("api_key"))))
        provider_used = ", ".join(active_providers) if active_providers else ("Multi-Engine Gateway" if or_key else "Local Engine Gateway")
        engine_errors: List[str] = []

        async def _evaluate_single_engine(
            client: httpx.AsyncClient,
            eng: Dict[str, Any],
            base_query: str,
            base_search_res: Optional[Dict[str, Any]],
        ) -> Tuple[EngineQueryResult, bool]:
            eng_name = eng["name"]

            if not eng.get("active", True):
                return self._engine_disabled(eng_name), False

            # Special case for Perplexity if base search already succeeded on perplexity
            if eng["id"] == "perplexity" and base_search_res and not base_search_res.get("error") and (
                base_search_res.get("content") or base_search_res.get("citations")
            ):
                res_obj = self._evaluate_engine_output(
                    engine_name=eng_name,
                    content=base_search_res.get("content", "") or "",
                    citations=base_search_res.get("citations", []) or [],
                    target_domain=target_domain,
                    brand=brand,
                )
                return res_obj, True

            m_res = await self._dispatch_engine_call(base_query, eng, client)
            if m_res.get("error") or not (m_res.get("content") or m_res.get("citations")):
                reason = m_res.get("error") or "Empty response from the model."
                code = str(m_res.get("status_code") or "empty")
                engine_errors.append(f"{eng_name}: {reason}")
                return self._engine_unavailable(eng_name, reason, code), False

            res_obj = self._evaluate_engine_output(
                engine_name=eng_name,
                content=m_res.get("content", "") or "",
                citations=m_res.get("citations", []) or [],
                target_domain=target_domain,
                brand=brand,
            )
            return res_obj, True

        async def _evaluate_query(client: httpx.AsyncClient, bq: Dict[str, str]) -> RealBuyerQueryEvaluation:
            base_query = bq["query"]
            base_search_res: Optional[Dict[str, Any]] = None
            if perp_key and _engine_matches_active_provider("perplexity"):
                base_search_res = await self._query_perplexity_live(base_query, perp_key)
                if base_search_res.get("error"):
                    engine_errors.append(f"Perplexity: {base_search_res['error']}")
                    if not (base_search_res.get("content") or base_search_res.get("citations")):
                        base_search_res = None
            if (
                not base_search_res
                and or_key
                and settings.get_active_provider() == "openrouter"
            ):
                base_search_res = await self._query_openrouter_engine(base_query, "perplexity/sonar", or_key, client)
                if base_search_res.get("error"):
                    engine_errors.append(f"OpenRouter sonar: {base_search_res['error']}")
                    if not (base_search_res.get("content") or base_search_res.get("citations")):
                        base_search_res = None

            engine_task_results = await asyncio.gather(
                *[_evaluate_single_engine(client, eng, base_query, base_search_res) for eng in configured_engines]
            )
            engine_results = [r[0] for r in engine_task_results]
            query_had_live_data = any(r[1] for r in engine_task_results)

            if not query_had_live_data:
                first_reason = next((e.failure_reason for e in engine_results if e.failure_reason), "Active engines were unreached.")
                return RealBuyerQueryEvaluation(
                    query_id=bq["query_id"],
                    buyer_query=bq["query"],
                    commercial_intent=bq["intent"],
                    monthly_search_volume=None,
                    engines=list(engine_results),
                    overall_citation_status="Unmeasured",
                    primary_competitor_capturing="Unmeasured (engine offline)",
                    recommended_action=f"Fix the engine error first: {first_reason}",
                )

            has_dominant_link = any(eng.was_cited for eng in engine_results)
            has_any_mention = any(eng.was_mentioned for eng in engine_results)
            competitors_found = [eng.competitor_cited_instead for eng in engine_results if eng.competitor_cited_instead]
            primary_comp = competitors_found[0] if competitors_found else "None (Clean Citations)"
            if has_dominant_link:
                action = "Keep the citable 40–60 word definition and schema; engines already link the domain."
            elif has_any_mention:
                action = "You are mentioned without a URL. Add Organization schema, a canonical domain mention, and a quotable definition block."
            else:
                action = "Engines omitted the brand. Publish a factual identity block (who / offer / buyer) plus FAQPage schema on the homepage."

            return RealBuyerQueryEvaluation(
                query_id=bq["query_id"],
                buyer_query=bq["query"],
                commercial_intent=bq["intent"],
                monthly_search_volume=None,
                engines=list(engine_results),
                overall_citation_status="Dominant" if has_dominant_link else ("At Risk" if has_any_mention else "Omitted"),
                primary_competitor_capturing=primary_comp,
                recommended_action=action,
            )

        try:
            async with httpx.AsyncClient(timeout=ENGINE_TIMEOUT_SECONDS) as client:
                evaluations = list(
                    await asyncio.wait_for(
                        asyncio.gather(*[_evaluate_query(client, bq) for bq in buyer_queries]),
                        timeout=DASHBOARD_TIMEOUT_SECONDS,
                    )
                )
        except asyncio.TimeoutError:
            return _unavailable_dashboard(
                target_domain=target_domain,
                provider_used=provider_used,
                failure_code="timeout",
                failure_reason=(
                    f"Live AI citation tracking is UNAVAILABLE. The engine fan-out exceeded "
                    f"{DASHBOARD_TIMEOUT_SECONDS:.0f}s. Engines were too slow or unreachable."
                ),
                next_steps=[
                    "Check engine API status and confirm provider keys have active credits.",
                    "Verify AI_CITATION_<ENGINE>_ACTIVE flags in backend/.env for engines you want to measure.",
                    "Confirm outbound HTTPS from this machine is not blocked.",
                ],
                engine_errors=engine_errors,
            )
        except Exception as exc:
            return _unavailable_dashboard(
                target_domain=target_domain,
                provider_used=provider_used,
                failure_code="request_failed",
                failure_reason=f"Live AI citation tracking is UNAVAILABLE. Request failed: {exc}",
                next_steps=[
                    "Read the error above. Typical causes: bad key, no credits, DNS/firewall, or a down provider.",
                    "Verify API keys in backend/.env and restart the API.",
                ],
                engine_errors=engine_errors + [str(exc)],
            )

        is_live = any(q.overall_citation_status != "Unmeasured" for q in evaluations)
        measured_engines = [
            eng_def["name"]
            for eng_def in configured_engines
            if any(
                getattr(eng, "extractability_health", "") not in ("UNAVAILABLE", "NOT_RUN", "DISABLED")
                for q in evaluations
                for eng in q.engines
                if eng.engine == eng_def["name"]
            )
        ]
        measured_count = len(measured_engines)

        if not is_live or measured_count == 0:
            unique_errors = []
            for err in engine_errors:
                if err not in unique_errors:
                    unique_errors.append(err)
            reason_bits = unique_errors[:4] or ["Active engines returned unverified or empty responses."]
            failure_reason = (
                "Live AI citation tracking is UNAVAILABLE or engines unreached. "
                + " | ".join(reason_bits)
                + " Citation score kept null (Zero-Fake standard)."
            )
            next_steps = [
                "Open the engine errors below. HTTP 401/403 = bad key. 402 = out of credits. 404 = model id not on this account. Timeout = network or provider lag.",
                "Verify API keys and model names in backend/.env for active engines.",
                "Disable unreachable engines via AI_CITATION_<ENGINE>_ACTIVE=false.",
                "Retry after fixing the first error. Score stays null until at least one engine answers.",
            ]
            return _unavailable_dashboard(
                target_domain=target_domain,
                provider_used=provider_used,
                failure_code="engines_unreached",
                failure_reason=failure_reason,
                next_steps=next_steps,
                engine_errors=unique_errors[:12],
            )

        total_evals = len(evaluations)
        engines_breakdown: Dict[str, float] = {}
        for eng_def in configured_engines:
            e_name = eng_def["name"]
            cited_count = sum(
                1 for q in evaluations for eng in q.engines if eng.engine == e_name and eng.was_cited
            )
            measured_for_engine = sum(
                1 for q in evaluations for eng in q.engines
                if eng.engine == e_name and eng.extractability_health not in ("UNAVAILABLE", "NOT_RUN", "DISABLED")
            )
            if measured_for_engine == 0:
                engines_breakdown[e_name] = 0.0
            else:
                engines_breakdown[e_name] = round((cited_count / measured_for_engine) * 100.0, 1)

        measured_pcts = [engines_breakdown[m] for m in measured_engines if m in engines_breakdown]
        overall_score = int(round(sum(measured_pcts) / len(measured_pcts))) if measured_pcts else None

        blindspots: List[str] = []
        for eng_name, pct in engines_breakdown.items():
            if eng_name not in measured_engines:
                err = next((e.failure_reason for q in evaluations for e in q.engines if e.engine == eng_name and e.failure_reason), None)
                if err:
                    blindspots.append(f"{eng_name} was not measured: {err}")
            elif pct < 50.0:
                blindspots.append(f"{eng_name} citation visibility is at risk ({pct}% citable responses across tracked queries).")

        unique_errors = []
        for err in engine_errors:
            if err not in unique_errors:
                unique_errors.append(err)

        active_count = len(active_engines)
        status_msg = (
            f"Live search-grounded citation evaluation active across {measured_count} of {active_count} active AI engines ({', '.join(measured_engines)})."
        )
        if unique_errors:
            status_msg += " Some engines encountered errors — see engine errors for details."

        return AiCitationTrackingDashboard(
            target_domain=target_domain,
            total_queries_tracked=total_evals,
            overall_ai_citation_score=overall_score,
            engines_breakdown=engines_breakdown,
            tracked_queries=evaluations,
            critical_ai_blindspots=blindspots,
            is_live=True,
            provider_used=provider_used,
            status_message=status_msg,
            engines_measured_count=measured_count,
            engines_total_count=active_count or len(configured_engines),
            failure_reason=None,
            failure_code=None,
            next_steps=[],
            engine_errors=unique_errors[:12],
        )


ai_citation_tracker = AiCitationTracker()
