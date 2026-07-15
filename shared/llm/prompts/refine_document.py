"""Chat-driven refinement for any doc_type (Phase 10). Same shape as the
pre-existing refine_cover_letter prompt, generalised across document types.
"""

import json
from typing import Any

SYSTEM = (
    "You are refining a PhD/postdoc application document via chat. Apply the "
    "user's instruction to the current draft; keep everything else intact "
    "unless asked otherwise. "
    'Output JSON: {"body_markdown": string, "reply": string (1 sentence '
    "describing what changed)}."
)


def build_user(
    doc_type: str,
    current_body: str,
    chat_history: list[dict[str, str]],
    user_message: str,
    *,
    profile: dict[str, Any],
    listing: dict[str, Any],
) -> str:
    history_text = "\n".join(f"{h.get('role')}: {h.get('content')}" for h in chat_history[-8:])
    return (
        f"DOC_TYPE: {doc_type}\n\n"
        "CURRENT DRAFT:\n" + current_body
        + "\n\nRECENT CHAT:\n" + history_text
        + "\n\nNEW INSTRUCTION:\n" + user_message
        + "\n\nPROFILE:\n" + json.dumps(profile, default=str)[:2000]
        + "\n\nLISTING:\n" + json.dumps(listing, default=str)[:2000]
    )
