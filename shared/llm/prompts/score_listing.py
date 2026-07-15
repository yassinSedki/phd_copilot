"""Score a listing against the user's profile.

AGENT.md §3.7: never ask the model for a 0–100 number (uncalibrated numbers
cluster at 72–85). The model fills a fixed rubric; the CODE computes the
total and applies hard-fail caps (unfunded when funding is required, degree
mismatch). The justification must cite specifics from BOTH documents.
"""

import json
from typing import Any

RUBRIC_MAX = {
    "topic_overlap": 30,
    "methods_match": 20,
    "eligibility": 20,
    "location_fit": 15,
    "deadline_feasibility": 15,
}

SYSTEM = (
    "You are scoring a PhD/postdoc opportunity against a researcher's "
    "profile by filling a fixed rubric. Return JSON with keys:\n"
    '"rubric": {"topic_overlap": 0-30, "methods_match": 0-20, '
    '"eligibility": 0-20, "location_fit": 0-15, "deadline_feasibility": 0-15},\n'
    '"flags": {"funding_confirmed": true|false|null (null = listing does not say), '
    '"degree_match": true|false|null (does the user\'s degree/career stage meet '
    "the listing's requirement)},\n"
    '"justification": one paragraph (2-4 sentences) citing SPECIFICS from both '
    "the profile and the listing — name the actual topics/methods that overlap "
    "or don't,\n"
    '"red_flags": array of strings (can be empty).\n'
    "deadline_feasibility scoring: you are given TODAY'S DATE — compare it to "
    "the listing's deadline yourself, don't just award full marks by default. "
    "No deadline stated -> 15 (nothing to be infeasible about). Deadline already "
    "passed -> 0, and add a red flag. Under 7 days away -> 3-6 (little time to "
    "prepare a strong application). 7-21 days -> 8-12. Over 21 days away -> 13-15.\n"
    "Do NOT output a total score — it is computed elsewhere. Output JSON only."
)


def build_user(profile: dict[str, Any], listing: dict[str, Any], today: str) -> str:
    return (
        f"TODAY'S DATE: {today}\n\n"
        "PROFILE:\n"
        + json.dumps(profile, default=str)[:4000]
        + "\n\nLISTING:\n"
        + json.dumps(listing, default=str)[:4000]
    )
