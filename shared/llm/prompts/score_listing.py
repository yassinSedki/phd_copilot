"""Score a listing against the user's profile (0–100 + fit breakdown)."""

import json
from typing import Any

SYSTEM = (
    "You are scoring a PhD/postdoc opportunity against a researcher's "
    "profile. Output JSON with keys: score (0-100 number), fit_breakdown "
    "(object with numeric keys: topic, methods, location, funding, "
    "career), reasons (2-3 sentence string), red_flags (array of "
    "strings, can be empty). Output JSON only."
)


def build_user(profile: dict[str, Any], listing: dict[str, Any]) -> str:
    return (
        "PROFILE:\n"
        + json.dumps(profile, default=str)[:4000]
        + "\n\nLISTING:\n"
        + json.dumps(listing, default=str)[:4000]
    )
