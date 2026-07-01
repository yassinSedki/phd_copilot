"""Cold email to a professor, grounded in deep-dive research."""

import json
from typing import Any

from shared.llm.types import ResearchSummary

SYSTEM = (
    "You draft a cold email to a professor about PhD opportunities. "
    "Reference at least one concrete piece of their recent work from "
    "the supplied research summary. Return JSON: subject, body. ≤200 words."
)


def build_user(profile: dict[str, Any], research: ResearchSummary) -> str:
    research_payload = {
        "summary": research.summary,
        "overlaps": research.overlaps,
        "recent_work": research.recent_work,
        "publications": research.publications,
    }
    return (
        f"PROFILE:\n{json.dumps(profile, default=str)[:3000]}\n\n"
        f"RESEARCH:\n{json.dumps(research_payload)[:4000]}"
    )
