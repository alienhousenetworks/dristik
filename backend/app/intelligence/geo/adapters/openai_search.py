"""
ChatGPT / OpenAI Search Engine Adapter.
Queries OpenAI's API to capture brand visibility and search-grounded citations.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
import httpx

from app.intelligence.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 14.0


class OpenAISearchAdapter(BaseGeoEngineAdapter):
    engine_id = "chatgpt"
    display_name = "ChatGPT (OpenAI)"
    default_model = "gpt-4o-mini"

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

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None
    ) -> EngineRawResponse:
        start_time = time.perf_counter()

        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                raw_content="",
                status_code=401,
                error="Missing OPENAI_API_KEY. Configure in backend/.env to query ChatGPT.",
                is_live=False,
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        endpoint = self.base_url if "/chat/completions" in self.base_url else f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a commercial search assistant. Answer factually, naming companies and citing source domains whenever known."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 350,
        }

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(endpoint, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""

                    # Extract inline URL citations if present
                    extracted_citations = re.findall(r"https?://[^\s\)\],>'\"]+", content)

                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=self.model,
                        raw_content=content,
                        citations=extracted_citations,
                        status_code=200,
                        latency_ms=latency,
                    )
                else:
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=self.model,
                        raw_content="",
                        status_code=res.status_code,
                        latency_ms=latency,
                        error=f"HTTP {res.status_code}: {res.text[:200]}",
                    )
            except httpx.TimeoutException:
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    raw_content="",
                    status_code=504,
                    latency_ms=latency,
                    error=f"Timeout after {DEFAULT_TIMEOUT_SECONDS}s contacting OpenAI.",
                )
            except Exception as exc:
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    raw_content="",
                    status_code=500,
                    latency_ms=latency,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
