"""Unified document drafting — cover_letter | sop | research_proposal
(Phase 10). Each doc_type has its own template under
worker/pipeline/draft/templates/; this prompt just tells the LLM how to fill
one in and to flag gaps.
"""

import json
from typing import Any

SYSTEM = (
    "You are drafting a PhD/postdoc application document for a researcher. "
    "You will be given a Markdown template: fill {{token}} placeholders "
    "exactly, and turn each [bracketed instruction] into real prose that "
    "follows it — never leave a literal {{token}} or [bracket] in the "
    "output. Write it as a natural, finished document, not a mad-libs fill-"
    "in — avoid repeating the same fact (the position title, institution "
    "name, or research field) more than once or twice across the whole "
    "document. If a field value is a taxonomy/breadcrumb string (e.g. "
    "'Engineering » Civil engineering, Knowledge engineering'), rephrase it "
    "in plain English rather than pasting it verbatim. Reference concrete "
    "details from the CV and listing where you can, and never invent "
    "achievements not supported by the profile. "
    'Output JSON: {"body_markdown": string, "author_notes": string (1-2 '
    "sentences on a specific choice you made, e.g. a paper you referenced), "
    '"warnings": string[] (requirements the listing mentions that the '
    "profile doesn't clearly satisfy — empty list if none)}."
)


def build_user(
    profile: dict[str, Any],
    listing: dict[str, Any],
    template: str,
    doc_type: str,
    red_flags: list[str],
) -> str:
    return (
        f"DOC_TYPE: {doc_type}\n\n"
        "TEMPLATE:\n" + template
        + "\n\nPROFILE:\n" + json.dumps(profile, default=str)[:4000]
        + "\n\nLISTING:\n" + json.dumps(listing, default=str)[:4000]
        + "\n\nRED FLAGS FROM SCORING:\n" + json.dumps(red_flags, default=str)
    )
