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
        # NVIDIA NIM does not host Anthropic/Google/OpenAI citation models; it must not act as the 6-engine gateway.
        assert main_citation_gateway() is None

        engines = {e["id"]: e for e in get_configured_ai_engines()}
        llama = engines.get("llama")
        assert llama is not None
        assert llama["provider"] == "nvidia"
        assert llama["api_key"] == "nvapi-citation-test"
        assert llama["model"] == "meta/llama-3.3-70b-instruct"
        for eid in ("claude", "gemini", "chatgpt", "qwen", "deepseek"):
            assert engines[eid]["provider"] != "nvidia"


def test_llm_client_exposes_configured_nvidia_model():
    from app.core.config import settings

    with patch.object(settings, "LLM_PROVIDER", "nvidia"), \
         patch.object(settings, "NVIDIA_API_KEY", "nvapi-test-key"), \
         patch.object(settings, "NVIDIA_MODEL", "nvidia/nemotron-3.5-super-vl-120b-a12b"), \
         patch.object(settings, "LLM_MODEL", None), \
         patch.object(settings, "NVIDIA_MODEL_FAST", None), \
         patch.object(settings, "LLM_MODEL_FAST", None):
        client = LLMClient(provider="nvidia")
        assert client.model == "nvidia/nemotron-3.5-super-vl-120b-a12b"


def test_dynamic_budget_call_cap_respects_floor():
    from app.core.inference.budget_manager import BudgetManager

    plan = BudgetManager.compute_audit_budget(5)
    assert plan.max_model_calls >= 150


@pytest.mark.asyncio
async def test_chapter_synthesizer_reads_content_key_from_llm_client():
    import json
    from unittest.mock import AsyncMock
    from app.reports.agentic_chapter_synthesizer import AgenticChapterSynthesizer

    mock_client = AsyncMock()
    mock_client.model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    mock_client.generate_chat_completion = AsyncMock(return_value={
        "content": json.dumps({
            "executive_summary": "Verified executive summary from content key.",
            "business_risk": "Risk detail.",
            "commercial_opportunity": "Opportunity detail.",
            "why_reader_should_care": "Care detail.",
            "recommended_action": "Action detail.",
            "priority_tier": "P1 (HIGH BUSINESS IMPACT)",
            "technical_mechanics": "Mechanics.",
            "root_cause_analysis": "Root cause.",
            "prescriptive_fix": "Fix.",
            "verification_protocol": "Verify.",
        }),
    })

    result = await AgenticChapterSynthesizer.synthesize_chapter_narrative_ai(
        book={"domain": "example.com", "pages": []},
        number="04",
        section={"id": "kw", "title": "Keyword Research"},
        findings=[],
        client=mock_client,
    )
    assert mock_client.generate_chat_completion.await_args.kwargs["model"] == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert "Verified executive summary from content key." in result["executive_summary"]


@pytest.mark.asyncio
async def test_benchmark_runner_short_circuits_on_http_410():
    from app.geo.benchmark_runner import GeoBenchmarkRunner
    from app.geo.adapters.base import BaseGeoEngineAdapter, EngineRawResponse

    calls = 0

    class GoneAdapter(BaseGeoEngineAdapter):
        engine_id = "chatgpt"
        display_name = "ChatGPT"

        def is_configured(self) -> bool:
            return True

        async def execute_query(self, query_text: str, locale: str = "en-US", client=None) -> EngineRawResponse:
            nonlocal calls
            calls += 1
            return EngineRawResponse(
                engine_id=self.engine_id,
                engine_name=self.display_name,
                model_version=self.model,
                raw_content="",
                status_code=410,
                error="HTTP 410: Gone",
            )

    runner = GeoBenchmarkRunner()
    adapter = GoneAdapter(api_key="test", model="openai/gpt-oss-20b")
    with patch("app.geo.benchmark_runner.get_available_adapters", return_value=[adapter]):
        report = await runner.execute_benchmark(
            domain="example.com",
            brand_name="Example",
            industry="Software",
            max_queries=6,
            repeats=1,
        )
    assert calls == 1
    assert report is not None
