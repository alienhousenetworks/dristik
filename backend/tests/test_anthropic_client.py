import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.inference.llm_client import LLMClient

@pytest.mark.asyncio
async def test_anthropic_client_temperature_in_extra_body():
    client = LLMClient(provider="anthropic", api_key="sk-ant-test")
    
    mock_msg = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Anthropic test response"
    mock_msg.content = [mock_block]
    mock_msg.usage = MagicMock(input_tokens=10, output_tokens=20)

    mock_messages = AsyncMock()
    mock_messages.create.return_value = mock_msg

    with patch("anthropic.AsyncAnthropic") as MockAsyncAnthropic:
        mock_instance = MockAsyncAnthropic.return_value
        mock_instance.messages = mock_messages
        mock_instance.close = AsyncMock()

        res = await client._generate_anthropic(
            model="claude-3-haiku-20240307",
            system_prompt="You are a helpful auditor.",
            user_prompt="Audit this website",
            temperature=0.3,
            max_tokens=500
        )

        assert res["content"] == "Anthropic test response"
        mock_messages.create.assert_called_once()
        called_kwargs = mock_messages.create.call_args.kwargs
        assert "temperature" not in called_kwargs
        assert called_kwargs.get("extra_body") == {"temperature": 0.3}
        assert called_kwargs.get("model") == "claude-3-haiku-20240307"
        assert called_kwargs.get("max_tokens") == 500
