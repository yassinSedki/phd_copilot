"""Initial cover letter draft from CV + listing + Markdown template."""

import json
from typing import Any

SYSTEM = (
    "You write a tailored cover letter. Use the provided template as "
    "scaffolding: fill the {{token}} placeholders in the header/sign-off "
    "exactly, and replace each [bracketed instruction] with real prose that "
    "follows that instruction — never leave a bracket or instruction text "
    "in the output. Rules for natural, non-templated writing:\n"
    "- State the position title and institution name ONCE, in the opening "
    "line only. Do not repeat them later in the letter.\n"
    "- Never paste a taxonomy/breadcrumb string verbatim (e.g. "
    "'Engineering » Civil engineering, Knowledge engineering'). Rephrase it "
    "as plain English ('civil and knowledge engineering').\n"
    "- Do not use markdown bold or meta-labels like 'In summary:' inside the "
    "letter body — write it as a normal formal letter would read on paper.\n"
    "- Every claim about the candidate's experience must be grounded in the "
    "profile — never invent projects, tools, or outcomes.\n"
    "- Keep it under 350 words total. Output the finished letter text only "
    "— no preamble, no notes about what you did."
)


def build_user(profile: dict[str, Any], listing: dict[str, Any], template: str) -> str:
    return (
        f"TEMPLATE:\n{template}\n\n"
        f"PROFILE:\n{json.dumps(profile, default=str)[:4000]}\n\n"
        f"LISTING:\n{json.dumps(listing, default=str)[:4000]}"
    )
