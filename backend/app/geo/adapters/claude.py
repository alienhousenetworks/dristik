"""Claude / Anthropic Engine Adapter.

Queries Anthropic's Messages API with optional native `web_search_20250305` server tool
(`API_WITH_SEARCH` when web search executes, honestly `API_MODEL_ONLY` otherwise).
Captures provider-reported model version, verified search citations, tokens, and search fees.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_WEB_SEARCH_TOOL_TYPE = "web_search_20250305"
DEFAULT_TIMEOUT_SECONDS = 18.0


def _extract_anthropic_search_citations(content_blocks: List[Dict[str, Any]]) -> tuple[List[str], List[Dict[str, Any]], int]:
    """Extract verified URLs strictly from Anthropic web_search tool results and citation blocks."""
    urls: List[str] = []
    sources: List[Dict[str, Any]] = []
    seen: set[str] = set()
    search_uses = 0

    def _add(url: str, title: str = "", origin: str = "anthropic_web_search") -> None:
        clean = str(url or "").strip().rstrip(".,);]>'\"")
        if not clean or not clean.startswith(("http://", "https://")) or clean in seen:
            return
        seen.add(clean)
        urls.append(clean)
        sources.append({"url": clean, "title": title, "origin": origin})

    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "server_tool_use" and block.get("name") == "web_search":
            search_uses += 1
        elif btype == "web_search_tool_result":
            for item in block.get("content") or []:
                if isinstance(item, dict) and item.get("type") == "web_search_result" and item.get("url"):
                    _add(item.get("url", ""), str(item.get("title") or ""), origin="web_search_tool_result")
        elif btype == "text":
            for cit in block.get("citations") or []:
                if isinstance(cit, dict) and cit.get("url"):
                    _add(cit.get("url", ""), str(cit.get("title") or ""), origin=str(cit.get("type") or "citation"))

    if search_uses == 0 and any(isinstance(b, dict) and b.get("type") == "web_search_tool_result" for b in content_blocks):
        search_uses = 1

    return urls, sources, search_uses


class ClaudeAdapter(BaseGeoEngineAdapter):
    engine_id = "claude"
    display_name = "Claude (Anthropic)"
    default_model = "claude-3-5-haiku-20241022"
    supported_models = [
        "claude-3-5-haiku-20241022",
        "claude-haiku-4-5-20251001",
        "claude-3-7-sonnet-20250219",
        "claude-sonnet-4-20250514",
    ]
    default_testing_mode = GEOTestingMode.API_WITH_SEARCH
    supports_web_search = True
    supports_citation_metadata = True
    supports_tool_use_metadata = True
    supports_geo_controls = False
    rate_limit_rpm = 200
    cost_per_1k_input_usd = 0.0008
    cost_per_1k_output_usd = 0.0040
    cost_per_search_use_usd = 0.01  # Anthropic native web_search: $10 per 1,000 searches
    unsupported_features = [
        "Consumer claude.ai account memory/projects differ from stateless Messages API.",
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
        env_search_enabled = str(
            os.environ.get(
                "ANTHROPIC_WEB_SEARCH_ENABLED",
                str(getattr(settings, "ANTHROPIC_WEB_SEARCH_ENABLED", True)),
            )
        ).lower() in ("true", "1", "yes")
        use_search = bool(enable_search and env_search_enabled)
        requested_mode = GEOTestingMode.API_WITH_SEARCH if use_search else GEOTestingMode.API_MODEL_ONLY

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
                testing_mode=requested_mode,
            )

        headers = {
            "x-api-key": self.api_key.strip(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "system": "You are a commercial knowledge engine. Answer objectively and concisely with facts, naming companies and citing verified sources.",
        }
        if use_search:
            max_uses = max(
                1,
                int(
                    os.environ.get(
                        "ANTHROPIC_WEB_SEARCH_MAX_USES",
                        str(getattr(settings, "ANTHROPIC_WEB_SEARCH_MAX_USES", 1)),
                    )
                ),
            )
            payload["tools"] = [
                {
                    "type": ANTHROPIC_WEB_SEARCH_TOOL_TYPE,
                    "name": "web_search",
                    "max_uses": max_uses,
                }
            ]

        async def _call(c: httpx.AsyncClient) -> EngineRawResponse:
            try:
                res = await c.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT_SECONDS)
                latency = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    content_blocks = data.get("content", []) or []
                    raw_text = "".join(
                        str(b.get("text", ""))
                        for b in content_blocks
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                    verified_urls, verified_sources, search_uses = _extract_anthropic_search_citations(content_blocks)
                    usage = data.get("usage") or {}
                    server_tool_use = usage.get("server_tool_use") or {}
                    if isinstance(server_tool_use, dict) and server_tool_use.get("web_search_requests"):
                        search_uses = max(search_uses, int(server_tool_use.get("web_search_requests") or 0))
                    p_tok = int(usage.get("input_tokens") or 0)
                    c_tok = int(usage.get("output_tokens") or 0)
                    search_executed = bool(use_search and (search_uses > 0 or verified_urls))
                    actual_mode = GEOTestingMode.API_WITH_SEARCH if search_executed else GEOTestingMode.API_MODEL_ONLY
                    return EngineRawResponse(
                        engine_id=self.engine_id,
                        engine_name=self.display_name,
                        model_version=str(data.get("model") or self.model),
                        requested_model=self.model,
                        raw_content=raw_text,
                        citations=verified_urls if search_executed else [],
                        sources=verified_sources if search_executed else [],
                        status_code=200,
                        is_live=True,
                        latency_ms=latency,
                        testing_mode=actual_mode,
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        estimated_cost_usd=self.estimate_cost_usd(
                            p_tok, c_tok, search_uses=search_uses if search_executed else 0
                        ),
                        tool_use_metadata={
                            "search_requested": use_search,
                            "search_executed": search_executed,
                            "web_search_requests": search_uses,
                            "verified_citations_count": len(verified_urls) if search_executed else 0,
                        },
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
                    testing_mode=requested_mode,
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
                    testing_mode=requested_mode,
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
                    testing_mode=requested_mode,
                    error=f"Request error: {exc}",
                )

        if client:
            return await _call(client)
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS) as local_client:
            return await _call(local_client)
