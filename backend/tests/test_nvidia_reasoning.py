"""Nemotron must not spend the JSON budget on its reasoning trace."""
from __future__ import annotations

import copy

import pytest

from app.core.inference.llm_client import (
    LLMClient,
    _nvidia_reasoning_fields,
    assemble_completion_text,
)


def test_nemotron_json_calls_disable_reasoning():
    fields = _nvidia_reasoning_fields(
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "DEFAULT",
    )
    assert fields == {"reasoning_effort": "none"}


def test_nemotron_prose_uses_low_effort_reasoning():
    fields = _nvidia_reasoning_fields("nvidia/nemotron-3.5-super-vl-120b-a12b", None)
    assert fields == {"reasoning_effort": "low"}


def test_non_nemotron_models_are_unchanged():
    assert _nvidia_reasoning_fields("meta/llama-3.3-70b-instruct", "DEFAULT") == {}


def test_reasoning_trace_is_not_treated_as_json():
    trace = "The user wants me to act as Dristik and simulate citation behaviors."
    assert assemble_completion_text("", trace, wants_json=True) == ""
    assert assemble_completion_text('{"ok": true}', trace, wants_json=True) == '{"ok": true}'
    assert assemble_completion_text("", '{"from": "trace"}', wants_json=True) == '{"from": "trace"}'
    assert assemble_completion_text("", trace, wants_json=False) == trace


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class _Client:
    def __init__(self, *args, **kwargs):
        self.payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, endpoint, json, headers):
        self.payloads.append(json)
        return _Response(
            200,
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"pillar": "aeo"}',
                            "reasoning_content": "The user wants a long plan.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8},
            },
        )


@pytest.mark.asyncio
async def test_nvidia_json_request_sends_reasoning_effort_none(monkeypatch):
    holder = {}

    def factory(*args, **kwargs):
        client = _Client()
        holder["client"] = client
        return client

    monkeypatch.setattr("app.core.inference.llm_client.httpx.AsyncClient", factory)
    client = LLMClient(
        api_key="test-key",
        base_url="https://integrate.api.nvidia.com/v1",
        provider="nvidia",
    )
    result = await client._single_chat_completion(
        provider="nvidia",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="test-key",
        extra_headers={},
        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        system_prompt="Return JSON.",
        user_prompt="Audit this page.",
        response_format="DEFAULT",
    )
    sent = holder["client"].payloads[0]
    assert sent["reasoning_effort"] == "none"
    assert "chat_template_kwargs" not in sent
    assert sent["response_format"] == {"type": "json_object"}
    assert result["content"] == '{"pillar": "aeo"}'
    assert "The user wants" not in result["content"]


@pytest.mark.asyncio
async def test_rejected_reasoning_effort_retries_with_thinking_disabled(monkeypatch):
    holder = {}

    class _RetryClient(_Client):
        async def post(self, endpoint, json, headers):
            self.payloads.append(copy.deepcopy(json))
            if len(self.payloads) == 1:
                rejected = _Response(400, {})
                rejected.text = "unknown field reasoning_effort"
                return rejected
            return _Response(
                200,
                {
                    "choices": [
                        {
                            "message": {"content": '{"pillar": "aeo"}'},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {},
                },
            )

    def factory(*args, **kwargs):
        client = _RetryClient()
        holder["client"] = client
        return client

    monkeypatch.setattr("app.core.inference.llm_client.httpx.AsyncClient", factory)
    client = LLMClient(
        api_key="test-key",
        base_url="https://integrate.api.nvidia.com/v1",
        provider="nvidia",
    )
    result = await client._single_chat_completion(
        provider="nvidia",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="test-key",
        extra_headers={},
        model="nvidia/nemotron-3.5-super-vl-120b-a12b",
        system_prompt="Return JSON.",
        user_prompt="Audit this page.",
        response_format="DEFAULT",
    )
    first, second = holder["client"].payloads
    assert first["reasoning_effort"] == "none"
    assert "chat_template_kwargs" not in first
    assert "reasoning_effort" not in second
    assert second["chat_template_kwargs"] == {"enable_thinking": False}
    assert result["content"] == '{"pillar": "aeo"}'
