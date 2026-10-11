import pytest
from unittest.mock import patch, AsyncMock
from app.intelligence.citations.tracker import AiCitationTracker, get_configured_ai_engines


@pytest.mark.asyncio
async def test_anthropic_direct_query_in_citation_tracker():
    tracker = AiCitationTracker()
    mock_res = {
        "content": "Claude confirms Acme is a top-tier provider.",
        "citations": [],
        "error": None,
        "status_code": 200,
    }
    with patch.object(tracker, "_query_anthropic_live", new_callable=AsyncMock, return_value=mock_res) as mock_anthropic, \
         patch.dict("os.environ", {
             "AI_CITATION_CROSS_PROVIDER": "false",
             "LLM_PROVIDER": "anthropic",
             "AI_CITATION_CLAUDE_ACTIVE": "true",
             "AI_CITATION_CLAUDE_PROVIDER": "anthropic",
             "AI_CITATION_CLAUDE_API_KEY": "sk-ant-test-key",
             "AI_CITATION_CLAUDE_MODEL": "claude-haiku-4-5-20251001",
             "AI_CITATION_CHATGPT_ACTIVE": "false",
             "AI_CITATION_GEMINI_ACTIVE": "false",
             "AI_CITATION_PERPLEXITY_ACTIVE": "false",
             "AI_CITATION_DEEPSEEK_ACTIVE": "false",
             "AI_CITATION_KIMI_ACTIVE": "false",
             "AI_CITATION_GROK_ACTIVE": "false",
             "AI_CITATION_LLAMA_ACTIVE": "false",
         }, clear=False):
        dash = await tracker.track_buyer_queries(
            domain="acmesoftware.in",
            biz_name="Acme Software",
            niche="FinTech SaaS"
        )
        assert dash.is_live is True
        assert dash.overall_ai_citation_score is not None
        assert mock_anthropic.called
        assert dash.engines_measured_count == 1
        # Inactive engines were skipped cleanly
        for query in dash.tracked_queries:
            claude_res = next(e for e in query.engines if e.engine == "Claude (Anthropic)")
            assert claude_res.extractability_health != "DISABLED"
            
            chatgpt_res = next(e for e in query.engines if e.engine == "ChatGPT (OpenAI)")
            assert chatgpt_res.extractability_health == "DISABLED"


def test_get_configured_ai_engines_env_overrides():
    with patch.dict("os.environ", {
        "AI_CITATION_CROSS_PROVIDER": "true",
        "AI_CITATION_CLAUDE_ACTIVE": "true",
        "AI_CITATION_CLAUDE_MODEL": "claude-sonnet-4-6",
        "AI_CITATION_CHATGPT_ACTIVE": "false",
        "AI_CITATION_DEEPSEEK_ACTIVE": "true",
        "AI_CITATION_DEEPSEEK_MODEL": "deepseek-reasoner",
    }, clear=False):
        engines = get_configured_ai_engines()
        engines_by_id = {e["id"]: e for e in engines}

        assert engines_by_id["claude"]["active"] is True
        assert engines_by_id["claude"]["model"] == "claude-sonnet-4-6"
        assert engines_by_id["chatgpt"]["active"] is False
        assert engines_by_id["deepseek"]["active"] is True
        assert engines_by_id["deepseek"]["model"] == "deepseek-reasoner"


def test_citation_engines_do_not_borrow_openrouter_without_explicit_provider():
    from app.core.config import settings, GROQ_DEFAULT_REASONING
    from app.core.config import Settings as SettingsCls

    with patch.object(settings, "LLM_PROVIDER", "anthropic"), \
         patch.object(settings, "OPENROUTER_API_KEY", "sk-or-v1-test"), \
         patch.object(settings, "OPENAI_API_KEY", None), \
         patch.object(settings, "DEEPSEEK_API_KEY", None), \
         patch.object(settings, "GEMINI_API_KEY", None), \
         patch.object(settings, "PERPLEXITY_API_KEY", None), \
         patch.dict("os.environ", {
             "AI_CITATION_CROSS_PROVIDER": "false",
             "AI_CITATION_CHATGPT_ACTIVE": "false",
             "AI_CITATION_GEMINI_ACTIVE": "false",
             "AI_CITATION_PERPLEXITY_ACTIVE": "false",
             "AI_CITATION_DEEPSEEK_ACTIVE": "false",
             "AI_CITATION_CHATGPT_PROVIDER": "openai",
             "AI_CITATION_DEEPSEEK_PROVIDER": "deepseek",
             "AI_CITATION_LLAMA_PROVIDER": "groq",
             "AI_CITATION_LLAMA_MODEL": "llama-3.3-70b-versatile",
             "AI_CITATION_LLAMA_ACTIVE": "true",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}
        assert engines["chatgpt"]["active"] is False
        assert engines["chatgpt"]["api_key"] in (None, "")
        assert engines["deepseek"]["active"] is False
        assert engines["gemini"]["active"] is False
        assert engines["llama"]["provider"] == "groq"
        assert engines["llama"]["active"] is False
        assert engines["llama"]["model"] == GROQ_DEFAULT_REASONING
        assert SettingsCls._coerce_groq_model(engines["llama"]["model"], GROQ_DEFAULT_REASONING) == GROQ_DEFAULT_REASONING


def test_anthropic_provider_does_not_activate_groq_citation_engine():
    from app.core.config import settings

    with patch.object(settings, "LLM_PROVIDER", "anthropic"), \
         patch.object(settings, "GROQ_API_KEY", "gsk_test"), \
         patch.object(settings, "ANTHROPIC_API_KEY", "sk-ant-test"), \
         patch.dict("os.environ", {
             "AI_CITATION_CROSS_PROVIDER": "false",
             "AI_CITATION_CLAUDE_ACTIVE": "true",
             "AI_CITATION_CLAUDE_PROVIDER": "anthropic",
             "AI_CITATION_LLAMA_ACTIVE": "true",
             "AI_CITATION_LLAMA_PROVIDER": "groq",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}
        assert engines["claude"]["active"] is True
        assert engines["claude"]["provider"] in ("anthropic", "claude")
        assert engines["llama"]["active"] is False
        assert engines["llama"]["provider"] == "groq"


def test_six_models_share_the_admin_gateway_key():
    from app.core.config import settings
    from app.intelligence.geo.adapters.registry import get_available_adapters

    with patch.object(settings, "LLM_PROVIDER", "openrouter"), \
         patch.object(settings, "OPENROUTER_API_KEY", "sk-or-v1-one-key"), \
         patch.object(settings, "TOGETHER_API_KEY", None), \
         patch.dict("os.environ", {
             "LLM_PROVIDER": "openrouter",
             "AI_CITATION_CROSS_PROVIDER": "false",
             "AI_CITATION_PROVIDER": "",
             "AI_CITATION_CLAUDE_PROVIDER": "",
             "AI_CITATION_CLAUDE_API_KEY": "",
             "AI_CITATION_GEMINI_PROVIDER": "",
             "AI_CITATION_GEMINI_API_KEY": "",
             "AI_CITATION_CHATGPT_PROVIDER": "",
             "AI_CITATION_CHATGPT_API_KEY": "",
             "AI_CITATION_QWEN_PROVIDER": "",
             "AI_CITATION_QWEN_API_KEY": "",
             "AI_CITATION_DEEPSEEK_PROVIDER": "",
             "AI_CITATION_DEEPSEEK_API_KEY": "",
             "AI_CITATION_PERPLEXITY_PROVIDER": "",
             "AI_CITATION_PERPLEXITY_API_KEY": "",
             "AI_CITATION_CLAUDE_ACTIVE": "true",
             "AI_CITATION_GEMINI_ACTIVE": "true",
             "AI_CITATION_CHATGPT_ACTIVE": "true",
             "AI_CITATION_QWEN_ACTIVE": "true",
             "AI_CITATION_DEEPSEEK_ACTIVE": "true",
             "AI_CITATION_PERPLEXITY_ACTIVE": "true",
             "AI_CITATION_CLAUDE_MODEL": "anthropic/claude-haiku-4.5",
             "AI_CITATION_GEMINI_MODEL": "google/gemini-3.8-flash",
             "AI_CITATION_CHATGPT_MODEL": "openai/gpt-6.1-sol",
             "AI_CITATION_QWEN_MODEL": "qwen/qwen3.8-flash",
             "AI_CITATION_DEEPSEEK_MODEL": "deepseek/deepseek-v4.1-flash",
             "AI_CITATION_PERPLEXITY_MODEL": "perplexity/sonar",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}
        for eid in ("claude", "gemini", "chatgpt", "qwen", "deepseek", "perplexity"):
            assert engines[eid]["active"] is True
            assert engines[eid]["provider"] == "openrouter"
            assert engines[eid]["api_key"] == "sk-or-v1-one-key"

        adapters = get_available_adapters()
        assert {ad.engine_id for ad in adapters} >= {
            "claude", "gemini", "chatgpt", "qwen", "deepseek", "perplexity"
        }
        assert all(ad.api_key == "sk-or-v1-one-key" for ad in adapters if ad.engine_id in {
            "claude", "gemini", "chatgpt", "qwen", "deepseek", "perplexity"
        })
        assert all("openrouter.ai" in ad.base_url for ad in adapters if ad.engine_id == "claude")


def test_together_gateway_covers_the_same_six_models():
    from app.core.config import settings

    with patch.object(settings, "LLM_PROVIDER", "together"), \
         patch.object(settings, "TOGETHER_API_KEY", "tg-one-key"), \
         patch.object(settings, "OPENROUTER_API_KEY", None), \
         patch.dict("os.environ", {
             "LLM_PROVIDER": "together",
             "AI_CITATION_CROSS_PROVIDER": "false",
             "AI_CITATION_PROVIDER": "",
             "AI_CITATION_CLAUDE_PROVIDER": "",
             "AI_CITATION_CLAUDE_API_KEY": "",
             "AI_CITATION_GEMINI_API_KEY": "",
             "AI_CITATION_CHATGPT_API_KEY": "",
             "AI_CITATION_QWEN_API_KEY": "",
             "AI_CITATION_DEEPSEEK_API_KEY": "",
             "AI_CITATION_PERPLEXITY_API_KEY": "",
             "AI_CITATION_CLAUDE_ACTIVE": "true",
             "AI_CITATION_GEMINI_ACTIVE": "true",
             "AI_CITATION_CHATGPT_ACTIVE": "true",
             "AI_CITATION_QWEN_ACTIVE": "true",
             "AI_CITATION_DEEPSEEK_ACTIVE": "true",
             "AI_CITATION_PERPLEXITY_ACTIVE": "true",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}
        for eid in ("claude", "gemini", "chatgpt", "qwen", "deepseek", "perplexity"):
            assert engines[eid]["provider"] == "together"
            assert engines[eid]["api_key"] == "tg-one-key"
            assert engines[eid]["active"] is True


def test_openrouter_frontier_models_configuration():
    from app.core.config import settings

    with patch.object(settings, "OPENROUTER_API_KEY", "sk-or-v1-test-frontier-key"), \
         patch.dict("os.environ", {
             "AI_CITATION_PROVIDER": "openrouter",
             "AI_CITATION_CROSS_PROVIDER": "true",
             "AI_CITATION_GEMINI_MODEL": "google/gemini-3.8-flash",
             "AI_CITATION_CHATGPT_MODEL": "openai/gpt-6.1-sol",
             "AI_CITATION_CLAUDE_MODEL": "anthropic/claude-haiku-4.5",
             "AI_CITATION_QWEN_MODEL": "qwen/qwen3.8-flash",
             "AI_CITATION_DEEPSEEK_MODEL": "deepseek/deepseek-v4.1-flash",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}

        # Verify Gemini
        assert engines["gemini"]["active"] is True
        assert engines["gemini"]["provider"] == "openrouter"
        assert engines["gemini"]["model"] == "google/gemini-3.8-flash"
        assert engines["gemini"]["api_key"] == "sk-or-v1-test-frontier-key"

        # Verify OpenAI / ChatGPT
        assert engines["chatgpt"]["active"] is True
        assert engines["chatgpt"]["provider"] == "openrouter"
        assert engines["chatgpt"]["model"] == "openai/gpt-6.1-sol"
        assert engines["chatgpt"]["api_key"] == "sk-or-v1-test-frontier-key"

        # Verify Claude
        assert engines["claude"]["active"] is True
        assert engines["claude"]["provider"] == "openrouter"
        assert engines["claude"]["model"] == "anthropic/claude-haiku-4.5"
        assert engines["claude"]["api_key"] == "sk-or-v1-test-frontier-key"

        # Verify Qwen
        assert engines["qwen"]["active"] is True
        assert engines["qwen"]["provider"] == "openrouter"
        assert engines["qwen"]["model"] == "qwen/qwen3.8-flash"
        assert engines["qwen"]["api_key"] == "sk-or-v1-test-frontier-key"

        # Verify DeepSeek
        assert engines["deepseek"]["active"] is True
        assert engines["deepseek"]["provider"] == "openrouter"
        assert engines["deepseek"]["model"] == "deepseek/deepseek-v4.1-flash"
        assert engines["deepseek"]["api_key"] == "sk-or-v1-test-frontier-key"


def test_openrouter_frontier_models_defaults_without_explicit_models():
    """When models are not explicitly set in env, the openrouter defaults match the frontier IDs."""
    from app.core.config import settings

    with patch.object(settings, "OPENROUTER_API_KEY", "sk-or-v1-test-key"), \
         patch.dict("os.environ", {
             "AI_CITATION_PROVIDER": "openrouter",
             "AI_CITATION_CROSS_PROVIDER": "true",
             "AI_CITATION_GEMINI_MODEL": "",
             "AI_CITATION_CHATGPT_MODEL": "",
             "AI_CITATION_CLAUDE_MODEL": "",
             "AI_CITATION_QWEN_MODEL": "",
             "AI_CITATION_DEEPSEEK_MODEL": "",
         }, clear=False):
        engines = {e["id"]: e for e in get_configured_ai_engines()}
        assert engines["gemini"]["model"] == "google/gemini-3.8-flash"
        assert engines["chatgpt"]["model"] == "openai/gpt-6.1-sol"
        assert engines["claude"]["model"] == "anthropic/claude-haiku-4.5"
        assert engines["qwen"]["model"] == "qwen/qwen3.8-flash"
        assert engines["deepseek"]["model"] == "deepseek/deepseek-v4.1-flash"


@pytest.mark.asyncio
async def test_qwen_dispatch_via_openrouter():
    tracker = AiCitationTracker()
    mock_res = {
        "content": "Qwen model response analyzing Acme Software citations.",
        "citations": ["https://acmesoftware.in"],
        "error": None,
        "status_code": 200,
    }
    with patch.object(tracker, "_query_openrouter_engine", new_callable=AsyncMock, return_value=mock_res) as mock_or:
        eng_def = {
            "id": "qwen",
            "name": "Qwen (Alibaba)",
            "provider": "openrouter",
            "api_key": "sk-or-v1-test-qwen",
            "model": "qwen/qwen3.8-flash"
        }
        res = await tracker._dispatch_engine_call("What is Acme Software?", eng_def)
        assert res["content"] == "Qwen model response analyzing Acme Software citations."
        assert mock_or.called
        call_args = mock_or.call_args[0]
        assert call_args[0] == "What is Acme Software?"
        assert call_args[1] == "qwen/qwen3.8-flash"
        assert call_args[2] == "sk-or-v1-test-qwen"
