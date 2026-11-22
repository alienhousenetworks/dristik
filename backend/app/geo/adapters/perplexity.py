"""Perplexity Pro / Sonar Engine Adapter.

Natively search-grounded (`API_WITH_SEARCH`) with structured citation URLs.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 12.0


class PerplexityAdapter(BaseGeoEngineAdapter):
    engine_id = "perplexity"
    display_name = "Perplexity Pro"
    default_model = "sonar"
    supported_models = ["sonar", "sonar-pro", "sonar-reasoning"]
    default_testing_mode = GEOTestingMode.API_WITH_SEARCH
    supports_web_search = True
    supports_citation_metadata = True
    supports_tool_use_metadata = True
    supports_geo_controls = False
    rate_limit_rpm = 120
    cost_per_1k_input_usd = 0.001
    cost_per_1k_output_usd = 0.001
    cost_per_search_use_usd = 0.005  # Perplexity Sonar: $5 per 1,000 requests
    unsupported_features = [
        "Consumer Perplexity Pro Focus/Deep Research mode differs from standard Sonar API.",
    ]

    async def execute_prompt(
        self,
        request: EnginePromptRequest | Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        req = request if isinstance(request, EnginePromptRequest) else EnginePromptRequest(**request)
        return await self.execute_query(prompt=req.prompt, locale=req.locale, client=client, max_tokens=req.max_tokens)

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
        *,
        max_tokens: int = 400,
    ) -> EngineRawResponse:
        start_time = time.perf_counter()

        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=401,
                error="Missing PERPLEXITY_API_KEY. Configure in provider connections or backend/.env to query Perplexity.",
                is_live=False,
                testing_mode=GEOTestingMode.API_WITH_SEARCH,
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a web search answer engine. Answer accurately with facts and citations."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "return_citations": True,
        }

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(PERPLEXITY_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    citations = [str(u) for u in (data.get("citations") or []) if u]
                    search_results = data.get("search_results") or []
                    usage = data.get("usage") or {}
                    p_tok = int(usage.get("prompt_tokens") or 0)
                    c_tok = int(usage.get("completion_tokens") or 0)
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=str(data.get("model") or self.model),
                        requested_model=self.model,
                        raw_content=content,
                        citations=citations,
                        sources=search_results if isinstance(search_results, list) else [{"url": u, "origin": "sonar"} for u in citations],
                        status_code=200,
                        is_live=True,
                        latency_ms=latency,
                        testing_mode=GEOTestingMode.API_WITH_SEARCH,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        estimated_cost_usd=self.estimate_cost_usd(p_tok, c_tok, search_uses=1),
                        tool_use_metadata={"search_grounded": True, "native_citations_count": len(citations)},
                    )
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=res.status_code,
                    latency_ms=latency,
                    testing_mode=GEOTestingMode.API_WITH_SEARCH,
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
                    testing_mode=GEOTestingMode.API_WITH_SEARCH,
                    error=f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s contacting Perplexity API.",
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
                    testing_mode=GEOTestingMode.API_WITH_SEARCH,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
