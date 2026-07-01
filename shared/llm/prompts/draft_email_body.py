"""Short application enquiry email body."""

import json
from typing import Any

SYSTEM = (
    "You draft a short, professional cold email to apply to a research "
    "position. Return JSON: subject (string), body (string, ≤180 words, "
    "no markdown). Be specific to the role; do NOT promise things not "
    "in the profile."
)


def build_user(profile: dict[str, Any], listing: dict[str, Any]) -> str:
    return (
        f"PROFILE:\n{json.dumps(profile, default=str)[:3000]}\n\n"
        f"LISTING:\n{json.dumps(listing, default=str)[:3000]}"
    )
