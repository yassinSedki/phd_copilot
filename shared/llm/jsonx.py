"""Robust JSON extraction from free-form LLM output — the ONE shared
implementation. Handles ```json fences, chatty prefixes/suffixes, and
flags likely max_tokens truncation. Previously three variants existed
(standard.py, prefilter, bare json.loads in the deep-dive) and the weakest
one silently turned fenced replies into {}.
"""

from __future__ import annotations

import json
import re
from typing import Any

from shared.llm.errors import LLMError, LLMErrorCode


def extract_json(text: str) -> Any:
    """Pull a JSON object/array out of free-form LLM output. Raises LLMError
    (PARSE_ERROR) when nothing parseable is found."""

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    # A response that doesn't end in a closing bracket/brace is almost
    # always max_tokens truncation, not a genuinely malformed response —
    # worth distinguishing since the fix is different (raise max_tokens vs.
    # fix the prompt).
    looks_truncated = not text.rstrip().endswith(("}", "]"))
    suffix = " (looks truncated — response likely hit max_tokens; consider raising LLM__MAX_TOKENS)" if looks_truncated else ""
    raise LLMError(
        LLMErrorCode.PARSE_ERROR,
        f"Could not parse JSON from model output ({len(text)} chars){suffix}: "
        f"{text[:200]} ... {text[-100:] if len(text) > 300 else ''}",
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """Like extract_json but never raises and always returns a dict —
    for fail-open callers (prefilter, deep-dive nodes)."""
    try:
        data = extract_json(text)
    except LLMError:
        return {}
    return data if isinstance(data, dict) else {}
