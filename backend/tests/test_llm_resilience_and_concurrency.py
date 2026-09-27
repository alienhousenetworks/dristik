import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.config import settings
from app.inference.llm_client import (
    LLMClient,
    NonRetryableLLMError,
    RateLimitException,
    get_provider_semaphore,
    _PROVIDER_SEMAPHORES,
)
from app.inference.model_router import ModelRouter
from app.cognition.blackboard import CognitiveBlackboard
from app.orchestration.agent_pool import AgentPool
from app.agents.runtime.registry import AgentDefinition


@pytest.mark.asyncio
async def test_get_provider_semaphore_concurrency_limit():
    _PROVIDER_SEMAPHORES.clear()
    sem_anthropic = get_provider_semaphore("anthropic")
    assert sem_anthropic._value == getattr(settings, "LLM_MAX_CONCURRENCY", 2)

    sem_groq = get_provider_semaphore("groq")
    assert sem_groq._value >= 2


@pytest.mark.asyncio
async def test_anthropic_client_max_retries_zero():
    """Verify that AsyncAnthropic is instantiated with max_retries=0 to eliminate SDK retry storms."""
    client = LLMClient(provider="anthropic", api_key="sk-ant-test")
    mock_msg = MagicMock()
    mock_block = MagicMock(type="text", text='{"test": 1}')
    mock_msg.content = [mock_block]
    mock_msg.usage = MagicMock(input_tokens=10, output_tokens=10)

    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_msg

    with patch("anthropic.AsyncAnthropic") as MockAsyncAnthropic:
        mock_instance = MockAsyncAnthropic.return_value
        mock_instance.messages = mock_messages
        mock_instance.close = AsyncMock()

        res = await client._generate_anthropic(
            model="claude-haiku-4-5-20251001",
            system_prompt="sys",
            user_prompt="usr",
            temperature=0.2,
            max_tokens=100,
        )

        assert res["content"] == '{"test": 1}'
        MockAsyncAnthropic.assert_called_once()
        _, kwargs = MockAsyncAnthropic.call_args
        assert kwargs.get("max_retries") == 0


@pytest.mark.asyncio
async def test_anthropic_non_retryable_errors():
    """Verify 400, 401, 403, 404 raise NonRetryableLLMError and immediately abort retries."""
    import anthropic

    client = LLMClient(provider="anthropic", api_key="sk-ant-test")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.headers = {}

    with patch("anthropic.AsyncAnthropic") as MockAsyncAnthropic, \
         patch.object(settings, "ENABLE_CROSS_PROVIDER_CASCADE", False):
        mock_instance = MockAsyncAnthropic.return_value
        mock_instance.messages = AsyncMock()
        mock_instance.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API Key",
            response=mock_resp,
            body={"error": {"type": "authentication_error", "message": "Invalid API Key"}}
        )
        mock_instance.close = AsyncMock()

        with pytest.raises(NonRetryableLLMError) as exc_info:
            await client.generate_chat_completion(
                model="claude-haiku-4-5-20251001",
                system_prompt="sys",
                user_prompt="usr",
            )
        assert exc_info.value.status_code == 401
        # Authentication error should fail immediately without retrying 3 times
        assert mock_instance.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_anthropic_rate_limit_backoff():
    """Verify 429 raises RateLimitException with extracted delay and triggers backoff."""
    import anthropic

    client = LLMClient(provider="anthropic", api_key="sk-ant-test")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "2"}

    # Mock success on second attempt
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(type="text", text='{"ok": true}')]
    mock_msg.usage = MagicMock(input_tokens=5, output_tokens=5)

    with patch("anthropic.AsyncAnthropic") as MockAsyncAnthropic, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        mock_instance = MockAsyncAnthropic.return_value
        mock_instance.messages = AsyncMock()
        mock_instance.messages.create.side_effect = [
            anthropic.RateLimitError(
                message="Rate limit reached: try again in 2.0s",
                response=mock_resp,
                body={}
            ),
            mock_msg,
        ]
        mock_instance.close = AsyncMock()

        res = await client.generate_chat_completion(
            model="claude-haiku-4-5-20251001",
            system_prompt="sys",
            user_prompt="usr",
        )

        assert res["content"] == '{"ok": true}'
        assert mock_instance.messages.create.call_count == 2
        mock_sleep.assert_called_once()
        slept_time = mock_sleep.call_args[0][0]
        assert slept_time >= 2.0


@pytest.mark.asyncio
async def test_model_router_does_not_repeat_exhausted_retries():
    """Verify ModelRouter generates structured output and does not loop 4 times on rate limits."""
    router = ModelRouter()
    mock_client = AsyncMock()
    mock_client.provider = "anthropic"
    mock_client.generate_chat_completion.side_effect = RateLimitException("Rate limit exhausted", 5.0)
    router.client = mock_client

    result = await router.generate_structured(
        capability="test_cap",
        agent_role="Test Specialist",
        task_contract="Test contract",
        evidence_list=[],
        allow_fallback=False,
    )

    assert result["status"] == "unavailable"
    assert "llm_exhausted" in result["unavailable_reason"]
    # ModelRouter should stop after 1 attempt when LLMClient already raised RateLimitException
    assert mock_client.generate_chat_completion.call_count == 1


@pytest.mark.asyncio
async def test_agent_pool_timeout_isolation():
    """Verify a hanging agent times out without crashing the pool or hanging other agents."""
    mock_router = MagicMock()
    pool = AgentPool(mock_router)

    slow_defn = AgentDefinition(
        agent_id="test.slow.v3",
        agent_name="Slow Agent",
        domain="CONTENT",
        worker_type="specialist",
        description="Slow test specialist",
        capabilities=["content_audit"],
        timeout_sec=1,  # 1 second timeout
    )

    async def hanging_run(*args, **kwargs):
        await asyncio.sleep(5.0)
        return {"status": "completed"}

    mock_agent = MagicMock()
    mock_agent.definition = slow_defn
    mock_agent.run = hanging_run
    pool.agents["test.slow.v3"] = mock_agent

    blackboard = CognitiveBlackboard(run_id="run_test", website_url="https://example.com")

    # Override timeout_sec buffer for test speed
    with patch("app.orchestration.agent_pool.asyncio.wait_for", side_effect=asyncio.TimeoutError):
        res = await pool._run_one("test.slow.v3", blackboard)
        assert res["status"] == "unavailable"
        assert "timeout" in res["unavailable_reason"]
