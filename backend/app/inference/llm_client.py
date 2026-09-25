"""
Dristik AI Multi-Provider LLM Gateway Client
Unified HTTP client for OpenAI-compatible LLM inference across:
- Google Gemini (gemini-2.0-flash / gemini-1.5-flash via OpenAI endpoint)
- Groq (Ultra-fast LPU inference: Llama 3.3 70B / 3.1 8B / Qwen)
- OpenRouter (Multi-model aggregator: DeepSeek, Gemini, Llama)
- Together AI (Llama 3.3 70B / 3.1 8B Turbo)
Anthropic Claude uses the official anthropic SDK (Messages API).
"""
import logging
import re
import time
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings, Settings, ANTHROPIC_DEFAULT_FAST
from app.inference.pricing import provider_billed_usd

logger = logging.getLogger("dristik.llm_client")

class RateLimitException(Exception):
    def __init__(self, message: str, retry_after_seconds: float = 5.0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        provider: Optional[str] = None
    ):
        creds = settings.get_llm_credentials()
        self.provider = provider or creds.get("provider", "together")
        self.api_key = api_key or creds.get("api_key")
        self.base_url = (base_url or creds.get("base_url", "https://api.together.xyz/v1")).rstrip("/")
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self.extra_headers = creds.get("extra_headers", {})

    def _extract_retry_after(self, response: httpx.Response, err_msg: str) -> float:
        """Extracts seconds to wait from Retry-After header or error message text."""
        # 1. Header check
        retry_header = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if retry_header:
            try:
                return float(retry_header)
            except ValueError:
                pass
                
        # 2. Regex check for 'try again in Xs' or 'in X.Xs'
        match = re.search(r"try again in ([\d\.]+)s", err_msg, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
                
        match_ms = re.search(r"try again in ([\d\.]+)ms", err_msg, re.IGNORECASE)
        if match_ms:
            try:
                return float(match_ms.group(1)) / 1000.0
            except ValueError:
                pass
                
        return 5.0

    async def _generate_anthropic(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Native Anthropic Messages API via the official SDK."""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key, timeout=timeout or self.timeout)
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_prompt or " "}],
        }
        if system_prompt and system_prompt.strip():
            kwargs["system"] = system_prompt

        # Anthropic SDK 1.6.0+: 'temperature' is passed via extra_body
        if temperature is not None:
            kwargs["extra_body"] = {"temperature": float(temperature)}

        start_time = time.time()
        try:
            message = await client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            err_msg = str(e)
            retry_sec = 5.0
            if getattr(e, "response", None) is not None:
                retry_sec = self._extract_retry_after(e.response, err_msg)
            raise RateLimitException(
                f"LLM Provider 'anthropic' returned HTTP 429 (Rate Limit): {err_msg}",
                retry_after_seconds=retry_sec,
            )
        except anthropic.APIStatusError as e:
            err_msg = getattr(e, "message", None) or str(e)
            logger.error(
                "[LLMClient] Provider 'anthropic' returned HTTP %s for model '%s': %s",
                e.status_code, model, err_msg,
            )
            raise RuntimeError(
                f"LLM Provider 'anthropic' returned HTTP {e.status_code}: {err_msg}"
            )
        except anthropic.APIConnectionError as e:
            raise RuntimeError(f"Connection failed to LLM endpoint (anthropic): {str(e)}")
        finally:
            await client.close()

        content = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        usage = message.usage
        return {
            "content": content,
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "latency_ms": (time.time() - start_time) * 1000,
            "model": getattr(message, "model", None) or model,
            "provider": self.provider,
            "stop_reason": getattr(message, "stop_reason", None),
            "provider_cost_usd": provider_billed_usd(usage),
        }

    async def generate_chat_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 3000,
        response_format: Any = "DEFAULT",
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calls chat completion endpoint and returns content along with usage telemetry.
        Raises RateLimitException on HTTP 429 with parsed retry delay.
        """
        if not self.api_key or not self.api_key.strip():
            active_prov = settings.get_active_provider()
            raise ValueError(
                f"No API key configured for active provider '{active_prov}'. "
                f"Please set ANTHROPIC_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or TOGETHER_API_KEY in backend/.env."
            )

        call_timeout = timeout or self.timeout
        if self.provider in ["anthropic", "claude"]:
            model = Settings._coerce_anthropic_model(model, ANTHROPIC_DEFAULT_FAST)
            anthropic_system = system_prompt
            wants_json = response_format == "DEFAULT" or (
                isinstance(response_format, dict) and response_format.get("type") == "json_object"
            )
            if wants_json:
                anthropic_system = (
                    f"{system_prompt or ''}\n\n"
                    "Respond with a single valid JSON object only. "
                    "No markdown fences, no preamble, no trailing commentary."
                ).strip()
            logger.info("[LLMClient] Calling %s endpoint (model: '%s')", self.provider, model)
            return await self._generate_anthropic(
                model=model,
                system_prompt=anthropic_system,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=call_timeout,
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format == "DEFAULT":
            payload["response_format"] = {"type": "json_object"}
        elif response_format is not None:
            payload["response_format"] = response_format

        logger.info("[LLMClient] Calling %s endpoint (model: '%s')", self.provider, model)
        start_time = time.time()
        async with httpx.AsyncClient(timeout=call_timeout) as client:
            try:
                response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 429:
                    err_text = response.text
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_msg = err_text
                    retry_sec = self._extract_retry_after(response, err_msg)
                    raise RateLimitException(
                        f"LLM Provider '{self.provider}' returned HTTP 429 (Rate Limit): {err_msg}",
                        retry_after_seconds=retry_sec
                    )

                if response.status_code == 400 and ("response_format" in response.text.lower() or "json_object" in response.text.lower()):
                    payload_no_format = dict(payload)
                    payload_no_format.pop("response_format", None)
                    response = await client.post(endpoint, json=payload_no_format, headers=headers)

                if response.status_code != 200:
                    err_text = response.text
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", err_text)
                    except Exception:
                        err_msg = err_text
                    logger.error(
                        "[LLMClient] Provider '%s' returned HTTP %d for model '%s': %s",
                        self.provider, response.status_code, model, err_msg
                    )
                    raise RuntimeError(
                        f"LLM Provider '{self.provider}' returned HTTP {response.status_code}: {err_msg}"
                    )
                data = response.json()
            except httpx.RequestError as e:
                raise RuntimeError(f"Connection failed to LLM endpoint ({self.provider}): {str(e)}")

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {}) or {}
        return {
            "content": content,
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "latency_ms": (time.time() - start_time) * 1000,
            "model": data.get("model") or model,
            "provider": self.provider,
            "stop_reason": choice.get("finish_reason"),
            "provider_cost_usd": provider_billed_usd(usage),
        }
