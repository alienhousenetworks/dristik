"""
Opt-In Bright Data Consumer AI Surface Adapter (Phase 4).

Queries consumer-facing AI interfaces (ChatGPT, Perplexity, Gemini, Google AI Mode)
via Bright Data Web Scraper datasets with ISO country targeting (`market`), async
`snapshot_id` handoff polling, third-party citation noise filtering, and 20-minute TTL cache.

GOVERNANCE CONTRACT:
- Explicitly tags every observation with `GEOTestingMode.LIVE_PRODUCT_TEST` so it is
  never confused with parametric model APIs.
- Fails closed (`is_live=False`, HTTP 401) when `BRIGHT_DATA_KEY` is not configured.
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

BRIGHT_DATA_TRIGGER_URL = "https://api.brightdata.com/datasets/v3/scrape"
BRIGHT_DATA_SNAPSHOT_URL = "https://api.brightdata.com/datasets/v3/snapshot"
CACHE_TTL_SECONDS = 20 * 60

PROVIDER_DEFAULTS: Dict[str, Dict[str, str]] = {
    "chatgpt_consumer": {
        "display_name": "ChatGPT (Consumer UI via Bright Data)",
        "env": "BRIGHT_DATA_DATASET_CHATGPT",
        "dataset_id": "gd_m7aof0k82r803d5bjm",
        "base_url": "https://chatgpt.com/",
    },
    "perplexity_consumer": {
        "display_name": "Perplexity (Consumer UI via Bright Data)",
        "env": "BRIGHT_DATA_DATASET_PERPLEXITY",
        "dataset_id": "gd_m7dhdot1vw9a7gc1n",
        "base_url": "https://www.perplexity.ai/",
    },
    "gemini_consumer": {
        "display_name": "Gemini (Consumer UI via Bright Data)",
        "env": "BRIGHT_DATA_DATASET_GEMINI",
        "dataset_id": "gd_mbz66arm2mf9cu856y",
        "base_url": "https://gemini.google.com/",
    },
    "google_ai_mode": {
        "display_name": "Google AI Mode (Consumer UI via Bright Data)",
        "env": "BRIGHT_DATA_DATASET_GOOGLE_AI",
        "dataset_id": "gd_mcswdt6z2elth3zqr2",
        "base_url": "https://www.google.com/",
    },
}

_BLOCKED_HOSTS = (
    "chatgpt.com", "openai.com", "oaiusercontent.com", "perplexity.ai", "pplx.ai",
    "gemini.google.com", "google.com", "cloudfront.net", "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com", "googletagmanager.com", "google-analytics.com",
    "doubleclick.net", "w3.org", "schema.org",
)
_ASSET_EXT_RE = re.compile(r"\.(?:js|css|map|png|jpe?g|gif|svg|webp|ico|woff2?|ttf|mp4|mp3)(?:\?|$)", re.I)
_JUNK_PATHS = ("/signals/", "/pixel", "/tracking", "/beacon", "/analytics", "/wp-includes/")

_RESPONSE_CACHE: Dict[Tuple[str, str, str], Tuple[float, EngineRawResponse]] = {}


def filter_third_party_citations(urls: List[str]) -> List[str]:
    """Strip AI platform hosts, CDN assets, and tracking pixels from raw citations."""
    clean: List[str] = []
    seen: set[str] = set()
    for raw in urls:
        u = (raw or "").strip().rstrip(".,;)")
        if not u or u in seen:
            continue
        try:
            parsed = urlparse(u)
            if parsed.scheme not in ("http", "https"):
                continue
            host = (parsed.hostname or "").lower()
            if not host:
                continue
            if any(host == b or host.endswith(f".{b}") for b in _BLOCKED_HOSTS):
                continue
            if _ASSET_EXT_RE.search(parsed.path):
                continue
            if any(frag in parsed.path.lower() for frag in _JUNK_PATHS):
                continue
            seen.add(u)
            clean.append(u)
        except Exception:
            continue
    return clean


def _extract_answer_and_sources(payload: Any) -> Tuple[str, List[str]]:
    row = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(row, dict):
        return "", []
    answer = ""
    for key in ("answer_text", "answer", "response", "text", "markdown", "content"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            answer = val.strip()
            break
    raw_urls: List[str] = []
    for key in ("citations", "sources", "links", "links_attached", "web_search_results"):
        val = row.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    raw_urls.append(item)
                elif isinstance(item, dict):
                    for uk in ("url", "link", "href", "uri"):
                        if isinstance(item.get(uk), str):
                            raw_urls.append(item[uk])
                            break
    raw_urls.extend(re.findall(r"https?://[^\s\)\],>'\"]+", answer))
    return answer, filter_third_party_citations(raw_urls)


class BrightDataConsumerAdapter(BaseGeoEngineAdapter):
    """Opt-in Bright Data consumer-UI adapter with ISO country targeting."""

    default_testing_mode = GEOTestingMode.LIVE_PRODUCT_TEST
    supports_web_search = True
    supports_citation_metadata = True
    supports_tool_use_metadata = True
    supports_geo_controls = True
    cost_per_1k_input_usd = 0.0
    cost_per_1k_output_usd = 0.0
    cost_per_search_use_usd = 0.002

    def __init__(self, provider_id: str, api_key: str = "", dataset_id: str = ""):
        meta = PROVIDER_DEFAULTS.get(provider_id)
        if not meta:
            raise ValueError(f"Unsupported Bright Data consumer provider: {provider_id}")
        self.engine_id = provider_id
        self.display_name = meta["display_name"]
        self.base_url = meta["base_url"]
        self.dataset_id = dataset_id or os.environ.get(meta["env"], "") or meta["dataset_id"]
        super().__init__(api_key=api_key, model=f"brightdata:{self.dataset_id}")

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
            country=(req.market or "US").upper(),
        )

    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
        *,
        country: str = "US",
        poll_timeout_seconds: float = 90.0,
    ) -> EngineRawResponse:
        start = time.perf_counter()
        country_code = (country or "US").strip().upper()[:2] or "US"

        if not self.is_configured():
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                requested_model=self.model,
                raw_content="",
                status_code=401,
                error="Missing BRIGHT_DATA_KEY. Configure BRIGHT_DATA_KEY to enable consumer-UI tracking.",
                is_live=False,
                testing_mode=GEOTestingMode.LIVE_PRODUCT_TEST,
                tool_use_metadata={"country": country_code, "dataset_id": self.dataset_id},
            )

        cache_key = (self.engine_id, country_code, prompt.strip().lower())
        cached = _RESPONSE_CACHE.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = [{"url": self.base_url, "prompt": prompt, "country": country_code}]

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(
                    f"{BRIGHT_DATA_TRIGGER_URL}?dataset_id={self.dataset_id}&notify=false&include_errors=true",
                    headers=headers,
                    json=body,
                    timeout=90.0,
                )
                if res.status_code not in (200, 202):
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=self.model,
                        requested_model=self.model,
                        raw_content="",
                        status_code=res.status_code,
                        latency_ms=round((time.perf_counter() - start) * 1000, 1),
                        error=f"Bright Data HTTP {res.status_code}: {res.text[:200]}",
                        is_live=False,
                        testing_mode=GEOTestingMode.LIVE_PRODUCT_TEST,
                        tool_use_metadata={"country": country_code, "dataset_id": self.dataset_id},
                    )
                payload = res.json()
                snapshot_id = payload.get("snapshot_id") if isinstance(payload, dict) else None
                if snapshot_id:
                    deadline = time.monotonic() + poll_timeout_seconds
                    while time.monotonic() < deadline:
                        await asyncio.sleep(3.0)
                        poll = await c.get(
                            f"{BRIGHT_DATA_SNAPSHOT_URL}/{snapshot_id}?format=json",
                            headers=headers,
                            timeout=30.0,
                        )
                        if poll.status_code == 200:
                            payload = poll.json()
                            break
                        if poll.status_code != 202:
                            break

                answer, citations = _extract_answer_and_sources(payload)
                resp = EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content=answer,
                    citations=citations,
                    sources=[{"url": u, "origin": "brightdata_consumer_ui"} for u in citations],
                    status_code=200,
                    latency_ms=round((time.perf_counter() - start) * 1000, 1),
                    is_live=bool(answer),
                    testing_mode=GEOTestingMode.LIVE_PRODUCT_TEST,
                    estimated_cost_usd=self.cost_per_search_use_usd,
                    tool_use_metadata={
                        "country": country_code,
                        "dataset_id": self.dataset_id,
                        "snapshot_id": snapshot_id,
                    },
                    session_limitations=[
                        f"Consumer-UI observation via Bright Data from country={country_code}."
                    ],
                )
                if resp.is_live:
                    _RESPONSE_CACHE[cache_key] = (time.monotonic(), resp)
                return resp
            except Exception as exc:
                return EngineRawResponse(
                    engine_id=self.engine_id,
                    engine_name=self.display_name,
                    model_version=self.model,
                    requested_model=self.model,
                    raw_content="",
                    status_code=500,
                    latency_ms=round((time.perf_counter() - start) * 1000, 1),
                    error=f"Bright Data request error: {exc}",
                    is_live=False,
                    testing_mode=GEOTestingMode.LIVE_PRODUCT_TEST,
                    tool_use_metadata={"country": country_code, "dataset_id": self.dataset_id},
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=95.0) as local_client:
            return await _call(local_client)
