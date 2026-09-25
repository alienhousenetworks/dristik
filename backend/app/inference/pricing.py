"""USD cost for the provider and model that actually served a call.

Resolution order:
1. Amount the provider billed on this response (OpenRouter ``usage.cost``).
2. Rate you configured for that provider and model (``LLM_MODEL_PRICES``),
   then the blanket ``LLM_COST_*_PER_MILLION`` pair when both are set.
3. Published list price for that exact provider and model.
4. Unpriced. A missing rate is never filled with another model's price.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# USD per 1M tokens, (input, output). Checked 2026-09-24.
# Operator rates and a provider bill both override this card.
_LIST_USD_PER_MILLION: Dict[Tuple[str, str], Tuple[float, float]] = {
    ("anthropic", "claude-haiku-4-5-20251001"): (1.00, 5.00),
    ("anthropic", "claude-haiku-4-5"): (1.00, 5.00),
    ("anthropic", "claude-sonnet-4-6"): (3.00, 15.00),
    ("anthropic", "claude-opus-4-6"): (5.00, 25.00),
    ("anthropic", "claude-3-haiku-20240307"): (0.25, 1.25),
    ("anthropic", "claude-3-5-haiku-20241022"): (0.80, 4.00),
    ("anthropic", "claude-3-5-sonnet-20241022"): (3.00, 15.00),
    ("anthropic", "claude-3-5-sonnet-20240620"): (3.00, 15.00),
    ("anthropic", "claude-3-7-sonnet-20250219"): (3.00, 15.00),
    ("groq", "openai/gpt-oss-20b"): (0.075, 0.30),
    ("groq", "openai/gpt-oss-120b"): (0.15, 0.60),
    ("groq", "llama-3.1-8b-instant"): (0.05, 0.08),
    ("groq", "llama-3.3-70b-versatile"): (0.59, 0.79),
    ("gemini", "gemini-2.0-flash"): (0.10, 0.40),
    ("gemini", "gemini-2.5-flash"): (0.30, 2.50),
    ("gemini", "gemini-2.5-flash-lite"): (0.10, 0.40),
    ("gemini", "gemini-2.5-pro"): (1.25, 10.00),
    ("together", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"): (0.18, 0.18),
    ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): (0.88, 0.88),
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o-mini"): (0.15, 0.60),
}

_KNOWN_PROVIDERS = {
    "anthropic",
    "claude",
    "groq",
    "gemini",
    "google",
    "openrouter",
    "together",
    "openai",
    "deepseek",
    "perplexity",
    "xai",
    "moonshot",
    "custom",
}

_logged_bad_price_json = False


@dataclass(frozen=True)
class PriceQuote:
    cost_usd: Optional[float]
    basis: str  # provider_billed | operator_rate | list_price | unpriced


def canonical_provider(provider: Optional[str]) -> str:
    name = (provider or "").strip().lower()
    if name == "claude":
        return "anthropic"
    if name == "google":
        return "gemini"
    return name or "unknown"


def _finite_nonnegative(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def provider_billed_usd(usage) -> Optional[float]:
    """Account charge on a completion payload. Missing means the provider did not bill in-band."""
    if usage is None:
        return None
    if isinstance(usage, dict):
        raw = usage.get("cost")
        if raw is None and isinstance(usage.get("cost_details"), dict):
            raw = usage["cost_details"].get("upstream_inference_cost")
    else:
        raw = getattr(usage, "cost", None)
    return _finite_nonnegative(raw)


def _rate_pair(value) -> Optional[Tuple[float, float]]:
    if not isinstance(value, dict) or "input" not in value or "output" not in value:
        return None
    incoming = _finite_nonnegative(value.get("input"))
    outgoing = _finite_nonnegative(value.get("output"))
    if incoming is None or outgoing is None:
        return None
    return incoming, outgoing


def _split_price_key(key: str) -> Tuple[Optional[str], str]:
    text = key.strip()
    if "|" in text:
        provider, model = text.split("|", 1)
        return canonical_provider(provider), model.strip()
    if "/" in text:
        head, rest = text.split("/", 1)
        if head.strip().lower() in _KNOWN_PROVIDERS:
            return canonical_provider(head), rest.strip()
    return None, text


def parse_operator_rates(raw: Optional[str]) -> Dict[Tuple[str, str], Tuple[float, float]]:
    """Map (provider, model) to USD per 1M tokens. Empty provider matches any provider."""
    global _logged_bad_price_json
    if not raw or not str(raw).strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        if not _logged_bad_price_json:
            logger.warning("LLM_MODEL_PRICES is not valid JSON; those rates are ignored.")
            _logged_bad_price_json = True
        return {}
    if not isinstance(data, dict):
        return {}

    table: Dict[Tuple[str, str], Tuple[float, float]] = {}
    for key, value in data.items():
        pair = _rate_pair(value)
        if pair:
            provider, model = _split_price_key(str(key))
            if model:
                table[(provider or "", model)] = pair
            continue
        if not isinstance(value, dict):
            continue
        provider = canonical_provider(str(key))
        for model_key, rate in value.items():
            nested = _rate_pair(rate)
            model = str(model_key).strip()
            if nested and model:
                table[(provider, model)] = nested
    return table


def _tokens_cost(input_tokens: int, output_tokens: int, rates: Tuple[float, float]) -> float:
    incoming, outgoing = rates
    cost = (max(input_tokens, 0) / 1_000_000) * incoming + (max(output_tokens, 0) / 1_000_000) * outgoing
    return round(cost, 8)


def price_call(
    *,
    provider: Optional[str],
    model: Optional[str],
    input_tokens: int,
    output_tokens: int,
    provider_cost_usd: Optional[float] = None,
    operator_rates: Optional[Dict[Tuple[str, str], Tuple[float, float]]] = None,
    blanket_input_per_million: Optional[float] = None,
    blanket_output_per_million: Optional[float] = None,
) -> PriceQuote:
    billed = _finite_nonnegative(provider_cost_usd)
    if billed is not None:
        return PriceQuote(cost_usd=round(billed, 8), basis="provider_billed")

    provider_name = canonical_provider(provider)
    model_name = (model or "").strip()
    table = operator_rates or {}
    specific = table.get((provider_name, model_name)) or table.get(("", model_name))
    if specific:
        return PriceQuote(cost_usd=_tokens_cost(input_tokens, output_tokens, specific), basis="operator_rate")

    blanket_in = _finite_nonnegative(blanket_input_per_million)
    blanket_out = _finite_nonnegative(blanket_output_per_million)
    if blanket_in is not None and blanket_out is not None:
        return PriceQuote(
            cost_usd=_tokens_cost(input_tokens, output_tokens, (blanket_in, blanket_out)),
            basis="operator_rate",
        )

    listed = _LIST_USD_PER_MILLION.get((provider_name, model_name))
    if listed:
        return PriceQuote(cost_usd=_tokens_cost(input_tokens, output_tokens, listed), basis="list_price")
    return PriceQuote(cost_usd=None, basis="unpriced")


def price_call_from_settings(
    *,
    provider: Optional[str],
    model: Optional[str],
    input_tokens: int,
    output_tokens: int,
    provider_cost_usd: Optional[float] = None,
) -> PriceQuote:
    from app.core.config import settings

    return price_call(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider_cost_usd=provider_cost_usd,
        operator_rates=parse_operator_rates(getattr(settings, "LLM_MODEL_PRICES", None)),
        blanket_input_per_million=getattr(settings, "LLM_COST_INPUT_PER_MILLION", None),
        blanket_output_per_million=getattr(settings, "LLM_COST_OUTPUT_PER_MILLION", None),
    )
