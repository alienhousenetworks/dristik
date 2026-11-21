"""Claude / Anthropic Engine Adapter.

Queries Anthropic's Messages API (`API_MODEL_ONLY` unless web search tool is
explicitly configured) and captures provider-reported model version and tokens.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_TIMEOUT_SECONDS = 14.0


class ClaudeAdapter(BaseGeoEngineAdapter):
    engine_id = "claude"
    display_name = "Claude (Anthropic)"
    default_model = "claude-3-5-haiku-20241022"
    supported_models = ["claude-3-5-haiku-20241022", "claude-3-7-sonnet-20250219", "claude-sonnet-4-20250514"]
    default_testing_mode = GEOTestingMode.API_MODEL_ONLY
    supports_web_search = False
    supports_citation_metadata = False
    supports_tool_use_metadata = True
    supports_geo_controls = False
    rate_limit_rpm = 200
    cost_per_1k_input_usd = 0.0008
    cost_per_1k_output_usd = 0.0040
    unsupported_features = [
        "Standard Anthropic Messages API is parametric (API_MODEL_ONLY); no live web citation index unless search tool enabled.",
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
        max_tokens: int = 350,
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
                error="Missing ANTHROPIC_API_KEY. Configure in provider connections or backend/.env to query Claude.",
                is_live=False,
                testing_mode=GEOTestingMode.API_MODEL_ONLY,
            )

        headers = {
            "x-api-key": self.api_key.strip(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "system": "You are a commercial knowledge engine. Answer objectively and concisely with facts, naming companies and citing verified sources.",
        }

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    content_blocks = data.get("content", [])
                    raw_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                    citations = re.findall(r"https?://[^\s\)\],>'\"]+", raw_text)
                    usage = data.get("usage") or {}
                    p_tok = int(usage.get("input_tokens") or 0)
                    c_tok = int(usage.get("output_tokens") or 0)
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=str(data.get("model") or self.model),
                        requested_model=self.model,
                        raw_content=raw_text,
                        citations=citations,
                        status_code=200,
                        is_live=True,
                        latency_ms=latency,
                        testing_mode=GEOTestingMode.API_MODEL_ONLY,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        estimated_cost_usd=self.estimate_cost_usd(p_tok, c_tok),
                    )
                logger.warning("[ClaudeAdapter] HTTP %s (model: %s): %s", res.status_code, self.model, res.text[:300])
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=res.status_code,
                    latency_ms=latency,
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
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
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
                    error=f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s contacting Claude API.",
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
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
