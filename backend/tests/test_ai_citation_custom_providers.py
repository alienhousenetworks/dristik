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
