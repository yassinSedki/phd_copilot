"""Chat-driven refinement for a drafted email (Phase 13) — reference-request
and supervisor-outreach drafts. Same shape as refine_document.py, applied to
a subject+body pair instead of a markdown document.
"""

import json
from typing import Any

SYSTEM = (
    "You are refining a drafted email via chat instruction, on behalf of a "
    "PhD/postdoc applicant. Apply the user's instruction to the CURRENT "
    "subject/body; keep everything else intact unless asked otherwise. "
    "Never invent facts (names, papers, dates) that are not present in the "
    "context or the current draft. Plain-text email — never introduce "
    "markdown (**bold**, *italic*, # headers) even if the current body has "
    "none; strip it out if it's already there. "
    'Output JSON: {"subject": string, "body": string, "reply": string '
    "(1 sentence describing what changed)}. Output JSON only."
)


def build_user(
    kind: str,
    current_subject: str,
    current_body: str,
    chat_history: list[dict[str, str]],
    user_message: str,
    *,
    context: dict[str, Any],
) -> str:
    history_text = "\n".join(f"{h.get('role')}: {h.get('content')}" for h in chat_history[-8:])
    return (
        f"EMAIL KIND: {kind}\n\n"
        f"CURRENT SUBJECT: {current_subject}\n\n"
        "CURRENT BODY:\n" + current_body
        + "\n\nRECENT CHAT:\n" + history_text
        + "\n\nNEW INSTRUCTION:\n" + user_message
        + "\n\nCONTEXT:\n" + json.dumps(context, default=str)[:3000]
    )
