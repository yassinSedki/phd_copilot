"""Enrich a single listing from its OWN dedicated page (not the crowded
search-results page). One listing per call — much less likely to conflate
fields across listings than parsing 8-10 cards from one list-page blob.
"""

import json
from typing import Any

SYSTEM = (
    "You extract full structured details for ONE academic PhD/postdoc/job "
    "listing from its dedicated detail page (not a search-results page — "
    "this text describes exactly one position). "
    'Return JSON: {"title": string, "institution": string, "country": string, '
    '"city": string, "research_field": string, "offer_type": string, '
    '"funding_info": string, "deadline_text": string, "contact_email": string, '
    '"application_url": string, "description": string, '
    '"required_docs": string[]}. '
    "required_docs = ONLY the documents/materials the applicant must SUBMIT "
    "with the application (e.g. \"CV\", \"Cover letter\", \"Transcripts\", "
    "\"2 reference letters\", \"Research proposal\", \"Degree certificate\") — "
    "one document per element, short canonical names. NEVER include "
    "eligibility criteria, required skills, grades, or language-level "
    "requirements there; those belong in description. "
    "application_url = the page where the candidate actually applies for THIS "
    "position (or this page's own URL) — never a generic university homepage. "
    "A best-guess HINT (extracted earlier from a search-results card) is "
    "provided — use it only as a starting point. The detail page is the "
    "authoritative source: override any hint field the page contradicts or "
    "clarifies. Use null for a field genuinely absent from both the hint and "
    "the page. Output JSON only."
)


def build_user(hint: dict[str, Any], detail_text: str, source_url: str) -> str:
    return (
        f"HINT (from the search-results card):\n{json.dumps(hint, default=str)}\n\n"
        f"DETAIL PAGE URL: {source_url}\n\n"
        # 20k chars ≈ 5k tokens — a dedicated detail page describes ONE
        # listing, so give the model the whole fetch (enrich_listing caps at
        # 20k) instead of silently discarding the tail where required-docs
        # and deadline sections often live.
        f"DETAIL PAGE CONTENT:\n{detail_text[:20000]}"
    )
