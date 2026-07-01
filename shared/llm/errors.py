"""Typed LLM errors. Each provider's `_translate_error` re-raises SDK
exceptions as one of these so call sites handle ONE error type, not one per
provider (factory guide §9).
"""

from __future__ import annotations

from enum import Enum


class LLMErrorCode(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    BAD_REQUEST = "bad_request"
    PROVIDER_ERROR = "provider_error"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class LLMError(Exception):
    def __init__(self, code: LLMErrorCode, message: str):
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
