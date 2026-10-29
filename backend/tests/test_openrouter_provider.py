import pytest
from unittest.mock import patch
from app.core.config import (
    Settings,
    ANTHROPIC_DEFAULT_FAST,
    ANTHROPIC_DEFAULT_REASONING,
    ANTHROPIC_FALLBACK_MODEL,
    GROQ_DEFAULT_FAST,
    GROQ_DEFAULT_REASONING,
)
from app.inference.model_router import ModelRouter
from app.inference.llm_client import LLMClient

def test_openrouter_configuration():
    test_settings = Settings(
        LLM_PROVIDER="openrouter",
        OPENROUTER_API_KEY="sk-or-v1-test-key",
        LLM_MODEL="openai/gpt-4o",
        OPENROUTER_SITE_URL="https://test.dristik.ai",
        OPENROUTER_SITE_NAME="Dristik Test"
    )
    
    assert test_settings.get_active_provider() == "openrouter"
    creds = test_settings.get_llm_credentials()
    assert creds["provider"] == "openrouter"
    assert creds["api_key"] == "sk-or-v1-test-key"
    assert creds["base_url"] == "https://openrouter.ai/api/v1"
    assert creds["model_fast"] == "openai/gpt-4o"
    assert creds["model_reasoning"] == "openai/gpt-4o"
    assert creds["extra_headers"] == {
        "HTTP-Referer": "https://test.dristik.ai",
        "X-Title": "Dristik Test"
    }

def test_openrouter_granular_models():
    test_settings = Settings(
        LLM_PROVIDER="openrouter",
        OPENROUTER_API_KEY="sk-or-v1-test-key",
        OPENROUTER_MODEL_FAST="openai/gpt-4o-mini",
        OPENROUTER_MODEL_REASONING="openai/gpt-4o"
    )
    
    creds = test_settings.get_llm_credentials()
    assert creds["model_fast"] == "openai/gpt-4o-mini"
    assert creds["model_reasoning"] == "openai/gpt-4o"


def test_anthropic_prefers_anthropic_model_over_llm_model():
    test_settings = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="sk-ant-test-key",
        LLM_MODEL="dots-studio/dots-3-note-preview:free",
        ANTHROPIC_MODEL=ANTHROPIC_DEFAULT_FAST,
    )

    creds = test_settings.get_llm_credentials()
    assert creds["provider"] == "anthropic"
    assert creds["model_fast"] == ANTHROPIC_DEFAULT_FAST
    assert creds["model_reasoning"] == ANTHROPIC_DEFAULT_FAST


def test_anthropic_granular_models_win_over_llm_model():
    test_settings = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="sk-ant-test-key",
        LLM_MODEL="dots-studio/dots-3-note-preview:free",
        LLM_MODEL_FAST="openai/gpt-4o-mini",
        LLM_MODEL_REASONING="openai/gpt-4o",
        ANTHROPIC_MODEL=ANTHROPIC_DEFAULT_FAST,
        ANTHROPIC_MODEL_FAST=ANTHROPIC_DEFAULT_FAST,
        ANTHROPIC_MODEL_REASONING=ANTHROPIC_DEFAULT_REASONING,
    )

    creds = test_settings.get_llm_credentials()
    assert creds["model_fast"] == ANTHROPIC_DEFAULT_FAST
    assert creds["model_reasoning"] == ANTHROPIC_DEFAULT_REASONING


def test_anthropic_coerces_retired_model_ids():
    test_settings = Settings(
        LLM_PROVIDER="anthropic",
        ANTHROPIC_API_KEY="sk-ant-test-key",
        ANTHROPIC_MODEL="claude-3-haiku-20240307",
        ANTHROPIC_MODEL_REASONING="claude-3-5-sonnet-20241022",
    )

    creds = test_settings.get_llm_credentials()
    assert creds["model_fast"] == ANTHROPIC_DEFAULT_FAST
    assert creds["model_reasoning"] == ANTHROPIC_DEFAULT_REASONING


@pytest.mark.asyncio
async def test_anthropic_missing_model_does_not_retry_same_id():
    router = ModelRouter()
    router.client.provider = "anthropic"
    calls = []

    async def boom(*, model, **kwargs):
        calls.append(model)
        raise RuntimeError(f"LLM Provider 'anthropic' returned HTTP 404: model: {model}")

    router.client.generate_chat_completion = boom
    with patch("app.inference.model_router.settings") as mock_settings:
        mock_settings.has_active_llm_key = True
        mock_settings.LLM_MAX_RETRIES = 4
        mock_settings.LLM_TEMPERATURE = 0.2
        mock_settings.LLM_MAX_TOKENS = 3000
        mock_settings.get_llm_credentials.return_value = {
            "model_fast": ANTHROPIC_DEFAULT_FAST,
            "model_reasoning": ANTHROPIC_DEFAULT_FAST,
            "provider": "anthropic",
        }
        result = await router.generate_structured(
            capability="business",
            agent_role="test",
            task_contract="test",
            evidence_list=[],
            allow_fallback=False,
        )

    assert calls.count(ANTHROPIC_DEFAULT_FAST) == 1
    assert ANTHROPIC_FALLBACK_MODEL in calls
    assert result.get("status") == "unavailable"


def test_groq_coerces_retired_llama_ids_to_live_models():
    test_settings = Settings(
        LLM_PROVIDER="groq",
        GROQ_API_KEY="gsk_test",
        GROQ_MODEL_FAST="llama-3.1-8b-instant",
        GROQ_MODEL_REASONING="llama-3.3-70b-versatile",
    )
    creds = test_settings.get_llm_credentials()
    assert creds["model_fast"] == GROQ_DEFAULT_FAST
    assert creds["model_reasoning"] == GROQ_DEFAULT_REASONING
    assert Settings._coerce_groq_model("openai/gpt-oss-20b", GROQ_DEFAULT_FAST) == "openai/gpt-oss-20b"
    assert Settings._coerce_groq_model("qwen/qwen3.6-27b", GROQ_DEFAULT_FAST) == "qwen/qwen3.6-27b"
    assert Settings._coerce_groq_model("dots-studio/dots-3-note-preview:free", GROQ_DEFAULT_FAST) == GROQ_DEFAULT_FAST
