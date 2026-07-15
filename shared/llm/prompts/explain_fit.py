import json
from typing import Any

SYSTEM = (
    "You write a short natural-language paragraph explaining why a PhD/postdoc "
    "opportunity fits (or doesn't fit) a specific researcher. 3-5 sentences. "
    "Reference concrete elements from both sides — a research area, a method, "
    "a location match, a timing match, a red flag. Avoid hedging language "
    "('might', 'could'); state what's true. Output JSON: {\"paragraph\": string}."
)


def build_user(
    profile: dict[str, Any],
    listing: dict[str, Any],
    breakdown: dict[str, Any],
    reasons: str,
    red_flags: list[str],
) -> str:
    return (
        "PROFILE:\n" + json.dumps(profile, default=str)[:2500]
        + "\n\nLISTING:\n" + json.dumps(listing, default=str)[:2500]
        + "\n\nSCORE BREAKDOWN:\n" + json.dumps(breakdown, default=str)
        + "\n\nREASONS:\n" + reasons
        + "\n\nRED FLAGS:\n" + json.dumps(red_flags, default=str)
    )
