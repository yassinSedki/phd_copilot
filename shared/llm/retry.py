"""Bounded retry with exponential backoff for transient provider failures.

Only RATE_LIMIT and TIMEOUT are retried — auth/bad-request/parse errors are
deterministic and retrying them just doubles the bill. Before this existed,
the only "recovery" was falling straight back to stub output.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable, TypeVar

from shared.llm.errors import LLMError, LLMErrorCode

log = logging.getLogger("phd_copilot.llm")

TRANSIENT = (LLMErrorCode.RATE_LIMIT, LLMErrorCode.TIMEOUT)
MAX_ATTEMPTS = 3
BASE_DELAY_S = 2.0

T = TypeVar("T")


def call_with_retry(fn: Callable[[], T]) -> T:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except LLMError as exc:
            if exc.code not in TRANSIENT or attempt == MAX_ATTEMPTS:
                raise
            delay = BASE_DELAY_S * (2 ** (attempt - 1))
            log.warning("LLM %s — retry %d/%d in %.0fs", exc.code.name, attempt, MAX_ATTEMPTS - 1, delay)
            time.sleep(delay)
    raise AssertionError("unreachable")


async def acall_with_retry(fn: Callable[[], Awaitable[T]]) -> T:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await fn()
        except LLMError as exc:
            if exc.code not in TRANSIENT or attempt == MAX_ATTEMPTS:
                raise
            delay = BASE_DELAY_S * (2 ** (attempt - 1))
            log.warning("LLM %s — retry %d/%d in %.0fs", exc.code.name, attempt, MAX_ATTEMPTS - 1, delay)
            await asyncio.sleep(delay)
    raise AssertionError("unreachable")
