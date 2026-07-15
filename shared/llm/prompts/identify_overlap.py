"""Deep-dive: find ≤3 concrete overlaps between the user's CV and the prof's work."""

import json
from typing import Any

SYSTEM = (
    "Concrete-overlap extractor. If a personal_note is provided, reference "
    "it in the resulting overlap statement (e.g. tie it to a topic or "
    "publication). JSON only."
)


def build_user(
    professor_name: str,
    research_topics: list[str],
    publications: list[str],
    user_profile: dict[str, Any],
    personal_note: str | None = None,
) -> str:
    return (
        f"PROFESSOR: {professor_name}\n"
        f"TOPICS: {json.dumps(research_topics or [])[:1500]}\n"
        f"PUBLICATIONS: {json.dumps(publications or [])[:1500]}\n\n"
        f"USER PROFILE: {json.dumps(user_profile, default=str)[:3000]}\n\n"
        f"PERSONAL NOTE (from the user, optional): {personal_note or '(none)'}\n\n"
        "Identify up to 3 SPECIFIC overlaps between the user's background "
        "and the professor's work. Each overlap must reference something "
        "concrete (a topic, method, or paper title) — not a generic 'shared "
        "interest in ML'. If a personal_note is provided, reference it in "
        "the resulting overlap statement. Output JSON: "
        '{"overlaps": ["...", "..."]}.'
    )
