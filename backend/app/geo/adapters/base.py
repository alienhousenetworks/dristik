"""Base GEO Provider Adapter Interface — Phase 4.

Fails closed with zero fake data: records exact verbatim output, status codes,
latency, citations, testing mode (`API_MODEL_ONLY` vs `API_WITH_SEARCH` vs
`LIVE_PRODUCT_TEST`), token usage, cost estimate, tool metadata, and transparent
fallback provenance.
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.geo.models import GEOTestingMode, ProviderCapabilities


class EnginePromptRequest(BaseModel):
    prompt: str
    locale: str = "en-US"
    market: str = "US"
    language: str = "en"
    enable_search: bool = False
    allow_fallback: bool = False
    max_tokens: int = 400
    repetition_number: int = 1


class EngineRawResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    engine_id: str
    engine_name: str
    model_version: str
    requested_model: str = ""
    raw_content: str
    citations: List[str] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    status_code: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    queried_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_live: bool = False
    testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    tool_use_metadata: Dict[str, Any] = Field(default_factory=dict)
    session_limitations: List[str] = Field(
        default_factory=lambda: [
            "Stateless API request; does not replicate consumer chat UI personalization or browsing defaults."
        ]
    )


class BaseGeoEngineAdapter(ABC):
    """Canonical GEOProvider interface for all generative AI platform adapters."""

    engine_id: str = "unknown"
    display_name: str = "Unknown Provider"
    default_model: str = ""
    supported_models: List[str] = []
    default_testing_mode: GEOTestingMode = GEOTestingMode.API_MODEL_ONLY
    supports_web_search: bool = False
    supports_citation_metadata: bool = False
    supports_tool_use_metadata: bool = False
    supports_geo_controls: bool = False
    rate_limit_rpm: Optional[int] = None
    cost_per_1k_input_usd: float = 0.001
    cost_per_1k_output_usd: float = 0.003
    unsupported_features: List[str] = []

    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model or self.default_model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def estimate_cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        cost = (prompt_tokens / 1000.0) * self.cost_per_1k_input_usd + (
            completion_tokens / 1000.0
        ) * self.cost_per_1k_output_usd
        return round(cost, 6)

    @abstractmethod
    async def execute_query(
        self,
        prompt: str,
        locale: str = "en-US",
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        """Execute a live query against the provider API; never simulates outputs."""
        pass

    async def execute_prompt(
        self,
        request: EnginePromptRequest | Dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> EngineRawResponse:
        req = request if isinstance(request, EnginePromptRequest) else EnginePromptRequest(**request)
        return await self.execute_query(prompt=req.prompt, locale=req.locale, client=client)

    def extract_citations(self, response: EngineRawResponse) -> List[str]:
        urls: List[str] = []
        seen = set()
        for u in list(response.citations or []) + re.findall(
            r"https?://[^\s\)\],>'\"]+", response.raw_content or ""
        ):
            clean = str(u).rstrip(".,);]>'\"")
            if clean and clean not in seen:
                seen.add(clean)
                urls.append(clean)
        return urls

    def normalize_response(self, response: EngineRawResponse) -> Dict[str, Any]:
        text = response.raw_content or ""
        return {
            "platform_id": response.engine_id,
            "platform_name": response.engine_name,
            "model_version": response.model_version,
            "requested_model": response.requested_model or self.model,
            "testing_mode": response.testing_mode.value,
            "response_text": text,
            "response_hash": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
            "citations": self.extract_citations(response),
            "sources": list(response.sources or []),
            "tool_use_metadata": dict(response.tool_use_metadata or {}),
            "fallback_used": response.fallback_used,
            "fallback_reason": response.fallback_reason,
            "is_live": response.is_live,
            "status_code": response.status_code,
            "latency_ms": response.latency_ms,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost_usd": response.estimated_cost_usd,
            "error": response.error,
            "queried_at": response.queried_at,
            "session_limitations": list(response.session_limitations or []),
        }

    def get_model_metadata(self) -> Dict[str, Any]:
        return {
            "platform_id": self.engine_id,
            "display_name": self.display_name,
            "model_name": self.model,
            "default_model": self.default_model,
            "testing_mode": self.default_testing_mode.value,
            "configured": self.is_configured(),
        }

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            platform_id=self.engine_id,
            display_name=self.display_name,
            supported_models=list(self.supported_models or ([self.model] if self.model else [])),
            default_model=self.model or self.default_model,
            text_response="Yes",
            search_grounded_response="Yes" if self.supports_web_search else "No",
            citation_metadata="Yes" if self.supports_citation_metadata else "No",
            tool_use_metadata="Yes" if self.supports_tool_use_metadata else "No",
            model_identification="Yes",
            geographic_controls="Yes" if self.supports_geo_controls else "No",
            repeatable_test_config="Partial",
            cost_estimation="Yes" if (self.cost_per_1k_input_usd or self.cost_per_1k_output_usd) else "Partial",
            rate_limit_rpm=self.rate_limit_rpm,
            est_cost_per_1k_input_tokens_usd=self.cost_per_1k_input_usd,
            est_cost_per_1k_output_tokens_usd=self.cost_per_1k_output_usd,
            default_testing_mode=self.default_testing_mode,
            unsupported_features=list(self.unsupported_features),
            auth_state="CONNECTED" if self.is_configured() else "NOT_CONFIGURED",
        )


# Canonical Phase 4 alias
GEOProvider = BaseGeoEngineAdapter
