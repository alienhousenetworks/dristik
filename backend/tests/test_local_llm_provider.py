"""Tests for first-class LLM_PROVIDER=local / LOCAL_LLM_MODEL env configuration."""
from app.core.config import Settings
from app.core.inference.pricing import price_call


def test_local_provider_env_model_and_base_url_resolution():
    cfg = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        LOCAL_LLM_MODEL="qwen2.5:1.5b-instruct",
        LOCAL_LLM_BASE_URL="http://127.0.0.1:11434/v1",
    )
    assert cfg.get_active_provider() == "local"
    assert cfg.has_active_llm_key is True

    creds = cfg.get_llm_credentials()
    assert creds["provider"] == "local"
    assert creds["base_url"] == "http://127.0.0.1:11434/v1"
    assert creds["model_fast"] == "qwen2.5:1.5b-instruct"
    assert creds["model_reasoning"] == "qwen2.5:1.5b-instruct"
    assert creds["api_key"] == "local"


def test_ollama_alias_and_split_fast_reasoning_local_models():
    cfg = Settings(
        _env_file=None,
        LLM_PROVIDER="ollama",
        LOCAL_LLM_MODEL_FAST="qwen2.5:1.5b-instruct",
        LOCAL_LLM_MODEL_REASONING="qwen2.5:3b-instruct",
    )
    assert cfg.get_active_provider() == "local"
    creds = cfg.get_llm_credentials()
    assert creds["provider"] == "local"
    assert creds["model_fast"] == "qwen2.5:1.5b-instruct"
    assert creds["model_reasoning"] == "qwen2.5:3b-instruct"


def test_local_provider_pricing_is_zero_usd_actual():
    quote = price_call(
        provider="local",
        model="qwen2.5:1.5b-instruct",
        input_tokens=5000,
        output_tokens=1500,
    )
    assert quote.cost_usd == 0.0
    assert quote.basis == "local_self_hosted"
    assert quote.is_actual is True
