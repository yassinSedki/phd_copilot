"""Anthropic provider — chat I/O only.

All application-level methods (parse_listing, score_listing, draft_*, etc.)
are inherited from StandardLLMClient. This file only knows how to send
messages and get a response back via langchain-anthropic.

SDK is lazy-imported in __init__ so the codebase remains runnable without
langchain-anthropic installed when LLM__PROVIDER!=anthropic (factory guide §9).
"""

from __future__ import annotations

from shared.llm.base import Message
from shared.llm.errors import LLMError, LLMErrorCode
from shared.llm.retry import acall_with_retry, call_with_retry
from shared.llm.standard import StandardLLMClient


def _translate_error(exc: Exception) -> "LLMError":
    msg = str(exc)
    lowered = msg.lower()
    if "rate" in lowered and "limit" in lowered:
        return LLMError(LLMErrorCode.RATE_LIMIT, msg)
    if "timeout" in lowered or "timed out" in lowered:
        return LLMError(LLMErrorCode.TIMEOUT, msg)
    if "auth" in lowered or "api key" in lowered or "401" in lowered:
        return LLMError(LLMErrorCode.AUTH, msg)
    if "400" in lowered or "bad request" in lowered:
        return LLMError(LLMErrorCode.BAD_REQUEST, msg)
    return LLMError(LLMErrorCode.PROVIDER_ERROR, msg)


class AnthropicLLMClient(StandardLLMClient):
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
            raise LLMError(LLMErrorCode.AUTH, "ANTHROPIC_API_KEY is not set.")

        try:
            from langchain_anthropic import ChatAnthropic  # lazy
        except ImportError as exc:
            raise LLMError(
                LLMErrorCode.PROVIDER_ERROR,
                "langchain-anthropic is not installed. "
                "pip install langchain-anthropic or pick a different LLM__PROVIDER.",
            ) from exc

        self._model = model
        self._json_mode = json_mode
        self._chat = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        self._init_fallback()

    def _to_langchain(self, messages: list[Message]):
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        out = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                out.append(SystemMessage(content=content))
            elif role == "assistant":
                out.append(AIMessage(content=content))
            else:
                out.append(HumanMessage(content=content))
        return out

    def invoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        def _once() -> str:
            try:
                result = self._chat.invoke(self._to_langchain(messages))
                return str(result.content)
            except Exception as exc:
                raise _translate_error(exc) from exc

        return call_with_retry(_once)

    async def ainvoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        async def _once() -> str:
            try:
                result = await self._chat.ainvoke(self._to_langchain(messages))
                return str(result.content)
            except Exception as exc:
                raise _translate_error(exc) from exc

        return await acall_with_retry(_once)
