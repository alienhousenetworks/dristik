"""Microsoft Copilot Engine Adapter.

Honestly reports UNAVAILABLE / NOT_CONFIGURED when no permitted Azure/Copilot
endpoint is configured. Never fabricates or substitutes an OpenAI API response
as Microsoft Copilot consumer visibility.
"""
from __future__ import annotations

import re
import time
from typing import Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse
from app.geo.models import GEOTestingMode

DEFAULT_TIMEOUT_SECONDS = 14.0


class CopilotAdapter(BaseGeoEngineAdapter):
    engine_id = "copilot"
    display_name = "Microsoft Copilot"
    default_model = "copilot-enterprise"
    supported_models = ["copilot-enterprise"]
    default_testing_mode = GEOTestingMode.API_WITH_SEARCH
    supports_web_search = True
    supports_citation_metadata = True
    supports_tool_use_metadata = False
    unsupported_features = [
        "Consumer Bing/Microsoft Copilot has no open public citation API; requires an authorized Azure/Copilot endpoint or manual observation.",
    ]

    def __init__(self, api_key: str = "", model: str = "", endpoint_url: str = ""):
        super().__init__(api_key=api_key, model=model)
        self.endpoint_url = (endpoint_url or "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.endpoint_url)

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        start_time = time.perf_counter()
        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=501,
                error="Microsoft Copilot endpoint & API key not configured (consumer Copilot surface is not queried via unauthenticated scraping).",
                is_live=False,
                testing_mode=GEOTestingMode.API_WITH_SEARCH,
            )

        headers = {"api-key": self.api_key.strip(), "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 350,
        }

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(self.endpoint_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    citations = [str(u) for u in (data.get("citations") or []) if u] or re.findall(r"https?://[^\s\)\],>'\"]+", content)
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=str(data.get("model") or self.model),
                        requested_model=self.model,
                        raw_content=content,
                        citations=citations,
                        status_code=200,
                        is_live=True,
                        latency_ms=latency,
                        testing_mode=GEOTestingMode.API_WITH_SEARCH,
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
            except Exception as exc:
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=500,
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
                    testing_mode=GEOTestingMode.API_WITH_SEARCH,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
