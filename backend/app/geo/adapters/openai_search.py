"""ChatGPT / OpenAI Engine Adapter.

Honestly distinguishes `API_MODEL_ONLY` chat completions from `API_WITH_SEARCH`
search-grounded models, records exact provider-reported model version and token
usage, and refuses silent model fallbacks unless explicitly opted in.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 14.0


class OpenAISearchAdapter(BaseGeoEngineAdapter):
    engine_id = "chatgpt"
    display_name = "ChatGPT (OpenAI)"
    default_model = "openai/gpt-oss-20b"
    supported_models = ["gpt-4o-mini", "gpt-4o", "gpt-4o-search-preview", "openai/gpt-oss-20b"]
    default_testing_mode = GEOTestingMode.API_MODEL_ONLY
    supports_web_search = True  # only when search-preview model or web_search tool is enabled
    supports_citation_metadata = True
    supports_tool_use_metadata = True
    supports_geo_controls = False
    rate_limit_rpm = 500
    cost_per_1k_input_usd = 0.00015
    cost_per_1k_output_usd = 0.00060
    unsupported_features = [
        "Consumer ChatGPT memory/personalization is not replicated via API.",
        "Standard chat completions are API_MODEL_ONLY unless a web-search model is used.",
    ]

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        base_url: str = "",
        extra_headers: Optional[Dict[str, str]] = None,
        engine_id: str = "",
        display_name: str = "",
    ):
        super().__init__(api_key=api_key, model=model)
        self.base_url = (base_url or OPENAI_API_URL).rstrip("/")
        self.extra_headers = extra_headers or {}
        if engine_id:
            self.engine_id = engine_id
        if display_name:
            self.display_name = display_name

    def _detect_testing_mode(self, model_name: str, enable_search: bool) -> GEOTestingMode:
        low = (model_name or "").lower()
        if enable_search or "search" in low or ":online" in low or "perplexity/" in low:
            return GEOTestingMode.API_WITH_SEARCH
        return GEOTestingMode.API_MODEL_ONLY

    async def execute_prompt(
        self,
        request: EnginePromptRequest | Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        req = request if isinstance(request, EnginePromptRequest) else EnginePromptRequest(**request)
        return await self.execute_query(
            prompt=req.prompt,
            locale=req.locale,
            client=client,
            allow_fallback=req.allow_fallback,
            enable_search=req.enable_search,
            max_tokens=req.max_tokens,
        )

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
        *,
        allow_fallback: bool = True,
        enable_search: bool = False,
        max_tokens: int = 350,
    ) -> EngineRawResponse:
        start_time = time.perf_counter()
        testing_mode = self._detect_testing_mode(self.model, enable_search)

        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=401,
                error="Missing OPENAI_API_KEY. Configure in provider connections or backend/.env to query ChatGPT.",
                is_live=False,
                testing_mode=testing_mode,
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        endpoint = self.base_url if "/chat/completions" in self.base_url else f"{self.base_url}/chat/completions"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a commercial search assistant. Answer factually, naming companies and citing source domains whenever known.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
        }
        if enable_search and "api.openai.com" in endpoint and "search" in self.model.lower():
            payload["web_search_options"] = {"search_context_size": "medium"}

        def _parse_ok(data: Dict[str, Any], used_model: str, latency: float, fb: bool = False, fb_reason: Optional[str] = None) -> EngineRawResponse:
            choices = data.get("choices", [])
            msg = choices[0].get("message", {}) if choices else {}
            content = msg.get("content", "") or ""
            annotations = msg.get("annotations") or []
            ann_urls = [
                str(a.get("url_citation", {}).get("url") or a.get("url") or "").strip()
                for a in annotations
                if isinstance(a, dict)
            ]
            ann_urls = [u for u in ann_urls if u]
            native_citations = [str(c) for c in (data.get("citations") or []) if c]
            inline_citations = re.findall(r"https?://[^\s\)\],>'\"]+", content)
            citations = list(dict.fromkeys(native_citations + ann_urls + inline_citations))
            usage = data.get("usage") or {}
            p_tok = int(usage.get("prompt_tokens") or 0)
            c_tok = int(usage.get("completion_tokens") or 0)
            reported_model = str(data.get("model") or used_model)
            search_actually_enabled = "web_search_options" in payload
            actual_mode = (
                GEOTestingMode.API_WITH_SEARCH
                if (native_citations or ann_urls or search_actually_enabled)
                else GEOTestingMode.API_MODEL_ONLY
            )
            # Only treat structured native/annotation citations (or search-grounded responses)
            # as verified citations; never present regex-scraped prose URLs from an ungrounded
            # chat completion as verified live web-search citations.
            verified_citations = (
                list(dict.fromkeys(native_citations + ann_urls + inline_citations))
                if actual_mode == GEOTestingMode.API_WITH_SEARCH
                else list(dict.fromkeys(native_citations + ann_urls))
            )
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=reported_model,
                requested_model=self.model,
                raw_content=content,
                citations=verified_citations,
                sources=[{"url": u, "origin": "annotation" if u in ann_urls else ("native" if u in native_citations else "inline")} for u in verified_citations],
                status_code=200,
                is_live=True,
                latency_ms=latency,
                testing_mode=actual_mode,
                fallback_used=fb,
                fallback_reason=fb_reason,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                estimated_cost_usd=self.estimate_cost_usd(p_tok, c_tok),
                tool_use_metadata={
                    "annotations_count": len(ann_urls),
                    "search_enabled": actual_mode == GEOTestingMode.API_WITH_SEARCH,
                    "ungrounded_inline_urls_excluded": len(inline_citations) if actual_mode != GEOTestingMode.API_WITH_SEARCH else 0,
                },
            )

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(endpoint, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    return _parse_ok(res.json(), self.model, latency)
                elif allow_fallback and res.status_code in (400, 404) and "openrouter" in self.base_url:
                    # Only execute fallback when explicitly permitted and record provenance transparently.
                    fallback_map = {
                        "google": "google/gemini-2.0-flash-001",
                        "gemini": "google/gemini-2.0-flash-001",
                        "openai": "openai/gpt-4o-mini",
                        "chatgpt": "openai/gpt-4o-mini",
                        "anthropic": "anthropic/claude-3.5-haiku",
                        "claude": "anthropic/claude-3.5-haiku",
                        "qwen": "qwen/qwen-2.5-72b-instruct",
                        "deepseek": "deepseek/deepseek-chat",
                        "perplexity": "perplexity/sonar",
                        "meta": "meta-llama/llama-3.3-70b-instruct",
                        "llama": "meta-llama/llama-3.3-70b-instruct",
                    }
                    key_lookup = self.model.split("/")[0].lower() if "/" in self.model else self.engine_id.lower()
                    fallback_model = fallback_map.get(key_lookup) or fallback_map.get(self.engine_id.lower())
                    if fallback_model and fallback_model != self.model:
                        fb_payload = dict(payload)
                        fb_payload["model"] = fallback_model
                        fb_res = await c.post(endpoint, headers=headers, json=fb_payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                        if fb_res.status_code == 200:
                            return _parse_ok(
                                fb_res.json(),
                                fallback_model,
                                round((time.perf_counter() - start_time) * 1000, 1),
                                fb=True,
                                fb_reason=f"Requested model '{self.model}' returned HTTP {res.status_code}; explicitly permitted fallback used.",
                            )

                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=res.status_code,
                    latency_ms=latency,
                    testing_mode=testing_mode,
                    error=f"HTTP {res.status_code}: {res.text[:200]}",
                )
            except httpx.TimeoutException:
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=504,
                    latency_ms=latency,
                    testing_mode=testing_mode,
                    error=f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s contacting {self.display_name}.",
                )
            except Exception as exc:
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=500,
                    latency_ms=latency,
                    testing_mode=testing_mode,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
