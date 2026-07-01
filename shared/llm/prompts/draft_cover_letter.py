"""Initial cover letter draft from CV + listing + Markdown template."""

import json
from typing import Any

SYSTEM = (
    "You write a tailored academic cover letter in Markdown. Use the "
    "provided template as scaffolding. Replace placeholder tokens with "
    "concrete content drawn from the profile and listing. Keep it under "
    "450 words. Output the Markdown letter only — no preamble."
)


def build_user(profile: dict[str, Any], listing: dict[str, Any], template: str) -> str:
    return (
        f"TEMPLATE:\n{template}\n\n"
        f"PROFILE:\n{json.dumps(profile, default=str)[:4000]}\n\n"
        f"LISTING:\n{json.dumps(listing, default=str)[:4000]}"
    )
