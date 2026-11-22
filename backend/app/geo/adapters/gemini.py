"""Google Gemini Engine Adapter.

Supports both standard `API_MODEL_ONLY` queries and optional Google Search
grounding (`API_WITH_SEARCH`) via Gemini's native `generateContent` endpoint.
Never mislabels an ungrounded chat completion as consumer Google AI Overviews.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_TIMEOUT_SECONDS = 14.0


class GeminiAdapter(BaseGeoEngineAdapter):
    engine_id = "gemini"
    display_name = "Google Gemini"
    default_model = "gemini-2.0-flash"
    supported_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    default_testing_mode = GEOTestingMode.API_MODEL_ONLY
    supports_web_search = True
    supports_citation_metadata = True
    supports_tool_use_metadata = True
    supports_geo_controls = False
    rate_limit_rpm = 300
    cost_per_1k_input_usd = 0.00010
    cost_per_1k_output_usd = 0.00040
    cost_per_search_use_usd = 0.035  # Google Search Grounding: $35 per 1,000 grounded requests
    unsupported_features = [
        "Google AI Overviews SERP surface is distinct from Gemini API.",
    ]

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
            enable_search=req.enable_search,
            max_tokens=req.max_tokens,
        )

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
        *,
        enable_search: bool = False,
        max_tokens: int = 350,
    ) -> EngineRawResponse:
        start_time = time.perf_counter()
        testing_mode = GEOTestingMode.API_WITH_SEARCH if enable_search else GEOTestingMode.API_MODEL_ONLY

        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=401,
                error="Missing GEMINI_API_KEY. Configure in provider connections or backend/.env to query Google Gemini.",
                is_live=False,
                testing_mode=testing_mode,
            )

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                if enable_search:
                    url = f"{GEMINI_NATIVE_BASE}/{self.model}:generateContent"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "tools": [{"google_search": {}}],
                        "generationConfig": {"maxOutputTokens": max_tokens},
                    }
                    res = await c.post(
                        url,
                        params={"key": self.api_key},
                        headers={"Content-Type": "application/json"},
                        json=payload,
                        timeout=DEFAULT_TIMEOUT_SECONDS,
                    )
                    latency = round((time.perf_counter() - start_time) * 1000, 1)
                    if res.status_code == 200:
                        data = res.json()
                        cand = (data.get("candidates") or [{}])[0]
                        parts = (cand.get("content") or {}).get("parts") or []
                        content = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
                        gm = cand.get("groundingMetadata") or {}
                        chunks = gm.get("groundingChunks") or []
                        grounding_urls = [
                            str((ch.get("web") or {}).get("uri", "")).strip()
                            for ch in chunks
                            if isinstance(ch, dict) and (ch.get("web") or {}).get("uri")
                        ]
                        inline = re.findall(r"https?://[^\s\)\],>'\"]+", content)
                        citations = list(dict.fromkeys(grounding_urls + inline))
                        usage = data.get("usageMetadata") or {}
                        p_tok = int(usage.get("promptTokenCount") or 0)
                        c_tok = int(usage.get("candidatesTokenCount") or 0)
                        search_used = bool(grounding_urls or (gm.get("webSearchQueries") or []))
                        actual_mode = GEOTestingMode.API_WITH_SEARCH if search_used else GEOTestingMode.API_MODEL_ONLY
                        return EngineRawResponse(
                            engine_id=self.engine_id,
                            engine_name=self.display_name,
                            model_version=str(data.get("modelVersion") or self.model),
                            requested_model=self.model,
                            raw_content=content,
                            citations=citations if search_used else [],
                            sources=[{"url": u, "origin": "google_search_grounding"} for u in grounding_urls],
                            status_code=200,
                            is_live=True,
                            latency_ms=latency,
                            testing_mode=actual_mode,
                            prompt_tokens=p_tok,
                            completion_tokens=c_tok,
                            estimated_cost_usd=self.estimate_cost_usd(
                                p_tok, c_tok, search_uses=1 if search_used else 0
                            ),
                            tool_use_metadata={
                                "web_search_queries": gm.get("webSearchQueries") or [],
                                "grounding_chunks_count": len(grounding_urls),
                                "search_executed": search_used,
                            },
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

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a commercial knowledge engine. Answer accurately with facts, companies, and authoritative sources.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                }
                res = await c.post(GEMINI_OPENAI_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    usage = data.get("usage") or {}
                    p_tok = int(usage.get("prompt_tokens") or 0)
                    c_tok = int(usage.get("completion_tokens") or 0)
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=str(data.get("model") or self.model),
                        requested_model=self.model,
                        raw_content=content,
                        citations=[],
                        status_code=200,
                        is_live=True,
                        latency_ms=latency,
                        testing_mode=GEOTestingMode.API_MODEL_ONLY,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        estimated_cost_usd=self.estimate_cost_usd(p_tok, c_tok, search_uses=0),
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
                    error=f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s contacting Gemini API.",
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
