"""Google Gemini Engine Adapter.

Supports both standard `API_MODEL_ONLY` queries and optional Google Search
grounding (`API_WITH_SEARCH`) via Gemini's native `generateContent` endpoint.
Never mislabels an ungrounded chat completion as consumer Google AI Overviews.
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from app.geo.adapters.base import BaseGeoEngineAdapter, EnginePromptRequest, EngineRawResponse
from app.geo.models import GEOTestingMode

GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_TIMEOUT_SECONDS = 14.0


def _clean_host(url_or_domain: str) -> str:
    raw = (url_or_domain or "").strip().lower()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw if "://" in raw else f"https://{raw}")
        return (parsed.hostname or "").removeprefix("www.")
    except Exception:
        return raw.removeprefix("www.").split("/")[0]


def parse_grounding_supports(gm: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Gemini groundingMetadata into normalized chunks and segment-level supports."""
    raw_chunks = gm.get("groundingChunks") or []
    chunks: List[Dict[str, str]] = []
    for ch in raw_chunks:
        if isinstance(ch, dict):
            web = ch.get("web") or {}
            chunks.append({
                "uri": str(web.get("uri") or "").strip(),
                "title": str(web.get("title") or "").strip(),
            })

    raw_supports = gm.get("groundingSupports") or []
    supports: List[Dict[str, Any]] = []
    for s in raw_supports:
        if not isinstance(s, dict):
            continue
        seg = s.get("segment") or {}
        supports.append({
            "start_index": int(seg.get("startIndex") or 0),
            "end_index": int(seg.get("endIndex") or 0),
            "text": str(seg.get("text") or ""),
            "chunk_indices": [int(i) for i in (s.get("groundingChunkIndices") or []) if isinstance(i, int)],
            "confidence_scores": [float(c) for c in (s.get("confidenceScores") or []) if isinstance(c, (int, float))],
        })

    return {
        "chunks": chunks,
        "supports": supports,
        "web_search_queries": [str(q) for q in (gm.get("webSearchQueries") or []) if q],
    }


def compute_selection_rate(
    target_url: str,
    chunks: List[Dict[str, str]],
    supports: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute exact grounding word-budget share (Selection Rate) attributed to target_url."""
    target_host = _clean_host(target_url)
    target_indices: List[int] = []
    if target_host:
        for idx, ch in enumerate(chunks):
            ch_host = _clean_host(ch.get("uri", ""))
            title_host = _clean_host(ch.get("title", ""))
            if (
                ch_host == target_host
                or ch_host.endswith(f".{target_host}")
                or title_host == target_host
                or title_host.endswith(f".{target_host}")
            ):
                target_indices.append(idx)

    target_set = set(target_indices)
    target_snippets: List[str] = []
    total_words = 0
    target_words = 0
    for sup in supports:
        text = (sup.get("text") or "").strip()
        words = len(text.split()) if text else 0
        total_words += words
        if any(i in target_set for i in (sup.get("chunk_indices") or [])):
            if text:
                target_snippets.append(text)
            target_words += words

    selection_rate = round(target_words / total_words, 4) if total_words > 0 else 0.0
    return {
        "target_url_found": len(target_indices) > 0,
        "target_chunk_indices": target_indices,
        "target_snippets": target_snippets,
        "total_grounding_words": total_words,
        "target_grounding_words": target_words,
        "selection_rate": selection_rate,
        "selection_rate_pct": round(selection_rate * 100.0, 1),
    }


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
                        parsed_gm = parse_grounding_supports(gm)
                        grounding_urls = [c["uri"] for c in parsed_gm["chunks"] if c["uri"]]
                        inline = re.findall(r"https?://[^\s\)\],>'\"]+", content)
                        citations = list(dict.fromkeys(grounding_urls + inline))
                        usage = data.get("usageMetadata") or {}
                        p_tok = int(usage.get("promptTokenCount") or 0)
                        c_tok = int(usage.get("candidatesTokenCount") or 0)
                        search_used = bool(grounding_urls or parsed_gm["web_search_queries"])
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
                                "web_search_queries": parsed_gm["web_search_queries"],
                                "grounding_chunks_count": len(grounding_urls),
                                "grounding_chunks": parsed_gm["chunks"],
                                "grounding_supports": parsed_gm["supports"],
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
