import json
from typing import Any

SYSTEM = (
    "You draft a polite, brief follow-up email to a professor who was asked "
    "for a reference letter and hasn't submitted it yet. Reference the "
    "original request date. Return JSON: {\"subject\": string, \"body\": string}. "
    "Keep it under 100 words, no guilt-tripping, assume good faith (they're busy). "
    "Plain-text email — never use markdown (**bold**, *italic*, # headers)."
)


def build_user(
    referee: dict[str, Any],
    position: dict[str, Any],
    sent_at: str | None,
    due_at: str | None,
) -> str:
    return json.dumps(
        {"referee": referee, "position": position, "sent_at": sent_at, "due_at": due_at},
        default=str,
    )
