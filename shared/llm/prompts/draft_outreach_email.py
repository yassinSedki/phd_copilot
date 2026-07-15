"""Cold email to a professor, grounded in deep-dive research."""

import json
from typing import Any

from shared.llm.types import ResearchSummary

SYSTEM = (
    "You draft a cold email to a professor about PhD opportunities. "
    "Reference at least one concrete piece of their recent work from "
    "the supplied research summary — a real publication title or a specific "
    "overlap point, quoted or closely paraphrased. If RESEARCH.publications "
    "is empty and RESEARCH.overlaps has nothing specific either, do NOT "
    "invent one: write honestly from RESEARCH.summary's general topics "
    "instead (e.g. 'your work on X'), and do not claim to have read a "
    "specific paper. NEVER output a bracketed placeholder like "
    "'[paper title]' or '[if available]' — an unfilled placeholder is "
    "worse than a more general sentence. This is a plain-text email, not "
    "markdown — never wrap words in ** or * for emphasis, never use "
    "markdown headers, and never use raw taxonomy/breadcrumb strings; write "
    "topic names in plain natural language. If a personal_note is "
    "provided, use it as the natural opener. Return JSON: subject, body. "
    "≤200 words."
)


def build_user(profile: dict[str, Any], research: ResearchSummary, personal_note: str | None = None) -> str:
    research_payload = {
        "summary": research.summary,
        "overlaps": research.overlaps,
        "recent_work": research.recent_work,
        "publications": research.publications,
    }
    return (
        f"PROFILE:\n{json.dumps(profile, default=str)[:3000]}\n\n"
        f"RESEARCH:\n{json.dumps(research_payload)[:4000]}\n\n"
        f"PERSONAL NOTE (from the user, optional): {personal_note or '(none)'}"
    )
