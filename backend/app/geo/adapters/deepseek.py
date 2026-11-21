"""DeepSeek Engine Adapter."""
from __future__ import annotations

import re
import time
from typing import Optional
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse
from app.geo.models import GEOTestingMode

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_TIMEOUT_SECONDS = 14.0


class DeepSeekAdapter(BaseGeoEngineAdapter):
    engine_id = "deepseek"
    display_name = "DeepSeek"
    default_model = "deepseek-chat"
    supported_models = ["deepseek-chat", "deepseek-reasoner"]
    default_testing_mode = GEOTestingMode.API_MODEL_ONLY
    supports_web_search = False
    supports_citation_metadata = False
    rate_limit_rpm = 120
    cost_per_1k_input_usd = 0.00027
    cost_per_1k_output_usd = 0.00110
    unsupported_features = [
        "DeepSeek API is parametric (API_MODEL_ONLY); web-browsing mode in consumer app is separate.",
    ]

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
                status_code=401,
                error="Missing DEEPSEEK_API_KEY. Configure in provider connections or backend/.env to query DeepSeek.",
                is_live=False,
                testing_mode=GEOTestingMode.API_MODEL_ONLY,
            )

        headers = {"Authorization": f"Bearer {self.api_key.strip()}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Answer factually and objectively, naming relevant companies and known source URLs."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 350,
        }

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)
                if res.status_code == 200:
                    data = res.json()
                    choices = data.get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    citations = re.findall(r"https?://[^\s\)\],>'\"]+", content)
                    usage = data.get("usage") or {}
                    p_tok, c_tok = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
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
                        testing_mode=GEOTestingMode.API_MODEL_ONLY,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        estimated_cost_usd=self.estimate_cost_usd(p_tok, c_tok),
                    )
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
            except Exception as exc:
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=500,
                    latency_ms=round((time.perf_counter() - start_time) * 1000, 1),
                    testing_mode=GEOTestingMode.API_MODEL_ONLY,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
