"""Conversational cover-letter refinement turn."""

import json
from typing import Any

from shared.llm.base import Message

SYSTEM = (
    "You refine a cover letter conversationally. Each turn, the user "
    "gives an instruction ('more concise', 'add my Graph RAG experience', "
    "'less formal', etc). Return ONLY a JSON object with two keys: "
    "letter (the full updated Markdown letter) and reply (one-sentence "
    "acknowledgement to the user). Output JSON only."
)


def build_user(
    current_markdown: str,
    chat_history: list[Message],
    user_message: str,
    *,
    profile: dict[str, Any],
    listing: dict[str, Any],
) -> str:
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in chat_history[-8:])
    return (
        f"CURRENT LETTER:\n{current_markdown}\n\n"
        f"CHAT HISTORY:\n{history_text}\n\n"
        f"USER MESSAGE:\n{user_message}\n\n"
        f"PROFILE:\n{json.dumps(profile, default=str)[:2000]}\n\n"
        f"LISTING:\n{json.dumps(listing, default=str)[:2000]}"
    )
