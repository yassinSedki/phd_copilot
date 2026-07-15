"""Cohere chat provider — chat I/O only.

Inherits parse_listing / score_listing / draft_* / etc. from
StandardLLMClient. Implements `invoke` / `ainvoke` via cohere.ClientV2.

cohere SDK is lazy-imported in __init__ so a project that uses
LLM__PROVIDER=stub or =anthropic doesn't pay the import cost.
"""

from __future__ import annotations

from shared.llm.base import Message
from shared.llm.errors import LLMError, LLMErrorCode
from shared.llm.retry import acall_with_retry, call_with_retry
from shared.llm.standard import StandardLLMClient


def _translate_error(exc: Exception) -> "LLMError":
    name = exc.__class__.__name__.lower()
    msg = str(exc)
    if "toomanyrequests" in name or "ratelimit" in name or "429" in msg:
        return LLMError(LLMErrorCode.RATE_LIMIT, msg)
    if "timeout" in name or "timeout" in msg.lower():
        return LLMError(LLMErrorCode.TIMEOUT, msg)
    if "unauthorized" in name or "401" in msg or "invalid api key" in msg.lower():
        return LLMError(LLMErrorCode.AUTH, msg)
    if "badrequest" in name or "400" in msg:
        return LLMError(LLMErrorCode.BAD_REQUEST, msg)
    return LLMError(LLMErrorCode.PROVIDER_ERROR, msg)


class CohereChatProvider(StandardLLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: int = 60,
        json_mode: bool = False,
    ) -> None:
        if not api_key:
            raise LLMError(LLMErrorCode.AUTH, "COHERE_API_KEY (LLM__API_KEY) is not set.")

        try:
            import cohere  # lazy
        except ImportError as exc:
            raise LLMError(
                LLMErrorCode.PROVIDER_ERROR,
                "cohere SDK is not installed. `poetry add cohere` or pick a different LLM__PROVIDER.",
            ) from exc

        self._model = model
        self._json_mode = json_mode
        self._temperature = temperature
        self._max_tokens = max_tokens

        self._client = cohere.ClientV2(api_key=api_key, timeout=timeout)
        self._async_client = cohere.AsyncClientV2(api_key=api_key, timeout=timeout)
        self._init_fallback()

    def _kwargs(self, json_mode: bool) -> dict:
        kw: dict = {
            "model": self._model,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        return kw

    @staticmethod
    def _extract_text(response) -> str:
        # cohere v5 ClientV2 chat response shape:
        #   response.message.content -> list[ContentBlock] where each has .text
        try:
            blocks = response.message.content
            if not blocks:
                return ""
            return "".join(getattr(b, "text", "") for b in blocks).strip()
        except AttributeError:
            return str(response)

    def invoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        def _once() -> str:
            try:
                response = self._client.chat(messages=messages, **self._kwargs(json_mode))
                return self._extract_text(response)
            except Exception as exc:
                raise _translate_error(exc) from exc

        return call_with_retry(_once)

    async def ainvoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        async def _once() -> str:
            try:
                response = await self._async_client.chat(messages=messages, **self._kwargs(json_mode))
                return self._extract_text(response)
            except Exception as exc:
                raise _translate_error(exc) from exc

        return await acall_with_retry(_once)
