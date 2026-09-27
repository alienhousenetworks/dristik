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

# USD per 1M tokens, (input, output). Checked 2026-09-27.
# Operator rates and a provider bill both override this card.
_LIST_USD_PER_MILLION: Dict[Tuple[str, str], Tuple[float, float]] = {
    # Anthropic
    ("anthropic", "claude-haiku-4-5-20251001"): (1.00, 5.00),
    ("anthropic", "claude-haiku-4-5"): (1.00, 5.00),
    ("anthropic", "claude-sonnet-4-6"): (3.00, 15.00),
    ("anthropic", "claude-opus-4-6"): (5.00, 25.00),
    ("anthropic", "claude-3-haiku-20240307"): (0.25, 1.25),
    ("anthropic", "claude-3-5-haiku-20241022"): (0.80, 4.00),
    ("anthropic", "claude-3-5-haiku"): (0.80, 4.00),
    ("anthropic", "claude-3-5-sonnet-20241022"): (3.00, 15.00),
    ("anthropic", "claude-3-5-sonnet-20240620"): (3.00, 15.00),
    ("anthropic", "claude-3-5-sonnet"): (3.00, 15.00),
    ("anthropic", "claude-3-7-sonnet-20250219"): (3.00, 15.00),
    ("anthropic", "claude-3-7-sonnet"): (3.00, 15.00),
    # Groq
    ("groq", "openai/gpt-oss-20b"): (0.075, 0.30),
    ("groq", "openai/gpt-oss-120b"): (0.15, 0.60),
    ("groq", "llama-3.1-8b-instant"): (0.05, 0.08),
    ("groq", "llama-3.3-70b-versatile"): (0.59, 0.79),
    ("groq", "llama-3.3-70b-specdec"): (0.59, 0.79),
    ("groq", "llama3-8b-8192"): (0.05, 0.08),
    ("groq", "llama3-70b-8192"): (0.59, 0.79),
    ("groq", "qwen/qwen3-32b"): (0.20, 0.20),
    ("groq", "qwen/qwen-2.5-32b"): (0.20, 0.20),
    ("groq", "deepseek-r1-distill-llama-70b"): (0.59, 0.79),
    # Google Gemini
    ("gemini", "gemini-2.0-flash"): (0.10, 0.40),
    ("gemini", "gemini-2.0-flash-exp"): (0.10, 0.40),
    ("gemini", "gemini-2.5-flash"): (0.30, 2.50),
    ("gemini", "gemini-2.5-flash-lite"): (0.10, 0.40),
    ("gemini", "gemini-2.5-pro"): (1.25, 10.00),
    ("gemini", "gemini-1.5-flash"): (0.075, 0.30),
    ("gemini", "gemini-1.5-pro"): (1.25, 5.00),
    # Together AI
    ("together", "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"): (0.18, 0.18),
    ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"): (0.88, 0.88),
    ("together", "meta-llama/Llama-3.2-3B-Instruct-Turbo"): (0.06, 0.06),
    ("together", "deepseek-ai/DeepSeek-V3"): (0.60, 1.25),
    ("together", "deepseek-ai/DeepSeek-R1"): (3.00, 7.00),
    # OpenAI
    ("openai", "gpt-4o"): (2.50, 10.00),
    ("openai", "gpt-4o-2024-08-06"): (2.50, 10.00),
    ("openai", "gpt-4o-mini"): (0.15, 0.60),
    ("openai", "gpt-4o-mini-2024-07-18"): (0.15, 0.60),
    ("openai", "gpt-4.1"): (2.00, 8.00),
    ("openai", "gpt-4.1-mini"): (0.15, 0.60),
    ("openai", "gpt-4.1-nano"): (0.08, 0.32),
    ("openai", "o3-mini"): (1.10, 4.40),
    ("openai", "o1-mini"): (1.10, 4.40),
    ("openai", "o1"): (15.00, 60.00),
    # DeepSeek
    ("deepseek", "deepseek-chat"): (0.14, 0.28),
    ("deepseek", "deepseek-reasoner"): (0.55, 2.19),
    # Perplexity
    ("perplexity", "sonar"): (1.00, 1.00),
    ("perplexity", "sonar-pro"): (3.00, 15.00),
    ("perplexity", "sonar-reasoning"): (1.00, 5.00),
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
    is_actual: bool


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


def extract_openrouter_cost(response_or_usage: Any) -> Optional[float]:
    """
    Extracts the actual billed dollar amount from OpenRouter API responses.
    OpenRouter returns 'cost' or 'cost_details.upstream_inference_cost' in its usage object.
    """
    if response_or_usage is None:
        return None

    usage = response_or_usage
    if isinstance(response_or_usage, dict):
        if "usage" in response_or_usage and isinstance(response_or_usage["usage"], dict):
            usage = response_or_usage["usage"]
        raw = usage.get("cost")
        if raw is None and isinstance(usage.get("cost_details"), dict):
            raw = usage["cost_details"].get("upstream_inference_cost")
    else:
        usage_obj = getattr(response_or_usage, "usage", response_or_usage)
        raw = getattr(usage_obj, "cost", None)
        if raw is None:
            details = getattr(usage_obj, "cost_details", None)
            if details is not None:
                raw = getattr(details, "upstream_inference_cost", None)
                if raw is None and isinstance(details, dict):
                    raw = details.get("upstream_inference_cost")

    return _finite_nonnegative(raw)


def extract_openai_cost(response_or_usage: Any) -> Optional[float]:
    """
    OpenAI inference API returns token usage data (prompt, completion, cached),
    not an in-band billed dollar amount per call. Returns None.
    """
    del response_or_usage
    return None


def extract_anthropic_cost(response_or_usage: Any) -> Optional[float]:
    """
    Anthropic Messages API returns token usage counts, not an in-band billed
    dollar amount per call. Returns None.
    """
    del response_or_usage
    return None


def extract_groq_cost(response_or_usage: Any) -> Optional[float]:
    """
    GroqCloud API returns token counts and queue timing metrics, not an in-band
    billed dollar amount per call. Returns None.
    """
    del response_or_usage
    return None


def extract_gemini_cost(response_or_usage: Any) -> Optional[float]:
    """
    Google Gemini returns token counts, not a final in-band dollar billing amount.
    Returns None.
    """
    del response_or_usage
    return None


def extract_together_cost(response_or_usage: Any) -> Optional[float]:
    """
    Together AI returns token counts, not an in-band dollar billing amount.
    Returns None.
    """
    del response_or_usage
    return None


def extract_provider_cost(provider: Optional[str], response_or_usage: Any) -> Optional[float]:
    """
    Adapter dispatcher: extracts actual provider-reported cost when supported.
    Only returns a float when the provider reported an actual account charge in-band.
    """
    canon = canonical_provider(provider)
    if canon == "openrouter":
        return extract_openrouter_cost(response_or_usage)
    if canon == "openai":
        return extract_openai_cost(response_or_usage)
    if canon == "anthropic":
        return extract_anthropic_cost(response_or_usage)
    if canon == "groq":
        return extract_groq_cost(response_or_usage)
    if canon == "gemini":
        return extract_gemini_cost(response_or_usage)
    if canon == "together":
        return extract_together_cost(response_or_usage)

    # For unknown / custom providers, inspect if usage explicitly provided a cost field
    return extract_openrouter_cost(response_or_usage)


def provider_billed_usd(usage: Any) -> Optional[float]:
    """Backward compatibility alias for extract_openrouter_cost."""
    return extract_openrouter_cost(usage)


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
        return PriceQuote(cost_usd=round(billed, 8), basis="provider_billed", is_actual=True)

    provider_name = canonical_provider(provider)
    model_name = (model or "").strip()
    table = operator_rates or {}
    specific = table.get((provider_name, model_name)) or table.get(("", model_name))
    if specific:
        return PriceQuote(
            cost_usd=_tokens_cost(input_tokens, output_tokens, specific),
            basis="operator_rate",
            is_actual=False,
        )

    blanket_in = _finite_nonnegative(blanket_input_per_million)
    blanket_out = _finite_nonnegative(blanket_output_per_million)
    if blanket_in is not None and blanket_out is not None:
        return PriceQuote(
            cost_usd=_tokens_cost(input_tokens, output_tokens, (blanket_in, blanket_out)),
            basis="operator_rate",
            is_actual=False,
        )

    # 1. Exact match in published list
    listed = _LIST_USD_PER_MILLION.get((provider_name, model_name))
    if listed:
        return PriceQuote(
            cost_usd=_tokens_cost(input_tokens, output_tokens, listed),
            basis="list_price",
            is_actual=False,
        )

    return PriceQuote(cost_usd=None, basis="unpriced", is_actual=False)


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
