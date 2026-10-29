import pytest
from unittest.mock import patch
from app.core.config import Settings
from app.core.inference.llm_client import LLMClient
from app.core.inference.pricing import canonical_provider
from app.geo.citations.tracker import get_configured_ai_engines, main_citation_gateway


def test_nvidia_configuration():
    test_settings = Settings(
        LLM_PROVIDER="nvidia",
        NVIDIA_API_KEY="nvapi-test-key",
        LLM_MODEL="meta/llama-3.3-70b-instruct",
    )
    
    assert test_settings.get_active_provider() == "nvidia"
    creds = test_settings.get_llm_credentials()
    assert creds["provider"] == "nvidia"
    assert creds["api_key"] == "nvapi-test-key"
    assert creds["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert creds["model_fast"] == "meta/llama-3.3-70b-instruct"
    assert creds["model_reasoning"] == "meta/llama-3.3-70b-instruct"
    assert creds["display_name"] == "NVIDIA NIM"


def test_nvidia_provider_aliases():
    for alias in ["nvidia", "nvidiaapi", "nim"]:
        s = Settings(LLM_PROVIDER=alias, NVIDIA_API_KEY="nvapi-test-key")
        assert s.get_active_provider() == "nvidia"
        creds = s.get_llm_credentials()
        assert creds["provider"] == "nvidia"

    # Also test togetherapi alias
    s_together = Settings(LLM_PROVIDER="togetherapi", TOGETHER_API_KEY="together-test-key")
    assert s_together.get_active_provider() == "together"


def test_nvidia_custom_base_url_and_models():
    test_settings = Settings(
        LLM_PROVIDER="nvidia",
        NVIDIA_API_KEY="nvapi-test-key",
        NVIDIA_BASE_URL="https://custom.nvidia.host/v1",
        NVIDIA_MODEL_FAST="meta/llama-3.1-8b-instruct",
        NVIDIA_MODEL_REASONING="meta/llama-3.3-70b-instruct",
    )
    
    creds = test_settings.get_llm_credentials()
    assert creds["base_url"] == "https://custom.nvidia.host/v1"
    assert creds["model_fast"] == "meta/llama-3.1-8b-instruct"
    assert creds["model_reasoning"] == "meta/llama-3.3-70b-instruct"


def test_nvidia_pricing_canonical_provider():
    assert canonical_provider("nvidia") == "nvidia"
    assert canonical_provider("nvidiaapi") == "nvidia"
    assert canonical_provider("nim") == "nvidia"
    assert canonical_provider("togetherapi") == "together"


def test_nvidia_citation_gateway_and_llama_engine():
    from app.core.config import settings

    with patch.object(settings, "LLM_PROVIDER", "nvidia"), \
         patch.object(settings, "NVIDIA_API_KEY", "nvapi-citation-test"), \
         patch.object(settings, "AI_CITATION_LLAMA_PROVIDER", "nvidia"), \
         patch.object(settings, "AI_CITATION_LLAMA_MODEL", None), \
         patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "nvidia",
                "NVIDIA_API_KEY": "nvapi-citation-test",
                "AI_CITATION_LLAMA_PROVIDER": "nvidia",
                "AI_CITATION_LLAMA_MODEL": "",
                "AI_CITATION_CROSS_PROVIDER": "false",
            },
            clear=False,
        ):
        gw = main_citation_gateway()
        assert gw is not None
        provider, key = gw
        assert provider == "nvidia"
        assert key == "nvapi-citation-test"

        engines = get_configured_ai_engines()
        llama = next((e for e in engines if e["id"] == "llama"), None)
        assert llama is not None
        assert llama["provider"] == "nvidia"
        assert llama["api_key"] == "nvapi-citation-test"
        assert llama["model"] == "meta/llama-3.3-70b-instruct"
