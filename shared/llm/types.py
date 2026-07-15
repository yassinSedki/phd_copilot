"""Shared LLM data types. Providers return these; pipeline consumes them.

Keeping the dataclasses out of `base.py` lets call sites import the types
without pulling in the ABC's transitive deps (langchain, langgraph).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# A line that's just a markdown divider ("---", "***", "___", optionally
# spaced out) or a handful of other giveaway artifacts models leave behind
# when asked to draft prose (section rules from a template, "Sincerely,"
# placeholders). Every user-facing dataclass below runs its prose fields
# through this in __post_init__ so no provider/prompt has to remember to.
_DIVIDER_LINE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def strip_ai_dividers(text: str) -> str:
    if not text:
        return text
    lines = [line for line in text.split("\n") if not _DIVIDER_LINE.match(line)]
    # Collapse any blank-line runs the removed dividers left behind.
    out: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        out.append(line)
    return "\n".join(out).strip()


@dataclass
class ParsedListing:
    title: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    research_field: Optional[str] = None
    offer_type: Optional[str] = None
    funding_info: Optional[str] = None
    deadline: Optional[datetime] = None
    contact_email: Optional[str] = None
    application_url: Optional[str] = None
    required_docs: list[str] = field(default_factory=list)
    description: Optional[str] = None
    parsed_ok: bool = True


@dataclass
class ScoreResult:
    score: float
    fit_breakdown: dict[str, float]
    reasons: str
    red_flags: list[str]
    model_used: str


@dataclass
class DraftedLetter:
    body_markdown: str
    model_used: str

    def __post_init__(self) -> None:
        self.body_markdown = strip_ai_dividers(self.body_markdown)


@dataclass
class RefinedLetter:
    body_markdown: str
    assistant_reply: str
    model_used: str

    def __post_init__(self) -> None:
        self.body_markdown = strip_ai_dividers(self.body_markdown)
        self.assistant_reply = strip_ai_dividers(self.assistant_reply)


@dataclass
class EmailBody:
    subject: str
    body: str
    model_used: str

    def __post_init__(self) -> None:
        self.body = strip_ai_dividers(self.body)


@dataclass
class ResearchSummary:
    summary: str
    overlaps: list[str]
    recent_work: list[str]
    publications: list[str] = field(default_factory=list)
    lab_url: Optional[str] = None
    model_used: str = ""

    def __post_init__(self) -> None:
        self.summary = strip_ai_dividers(self.summary)


@dataclass
class OutreachDraft:
    subject: str
    body: str
    model_used: str

    def __post_init__(self) -> None:
        self.body = strip_ai_dividers(self.body)


@dataclass
class ExtractedProfile:
    """Structured profile pulled from a CV by the LLM. Phase 03 onboarding."""

    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    research_summary: Optional[str] = None
    research_areas: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    programming_languages: list[str] = field(default_factory=list)
    degree_subject: Optional[str] = None
    graduation_year: Optional[int] = None
    career_stage: Optional[str] = None
    languages_spoken: list[str] = field(default_factory=list)
    publications: list[dict] = field(default_factory=list)
    geographic_hints: list[str] = field(default_factory=list)


@dataclass
class ReferenceEmailDraft:
    """A reference-request or follow-up email (Phase 12)."""

    subject: str
    body: str
    model_used: str = ""

    def __post_init__(self) -> None:
        self.body = strip_ai_dividers(self.body)


@dataclass
class DraftedDocument:
    """Unified document draft (Phase 10) — cover_letter | sop | research_proposal."""

    body_markdown: str
    author_notes: str = ""
    warnings: list[str] = field(default_factory=list)
    model_used: str = ""

    def __post_init__(self) -> None:
        self.body_markdown = strip_ai_dividers(self.body_markdown)
        self.author_notes = strip_ai_dividers(self.author_notes)


@dataclass
class RefinedDocument:
    body_markdown: str
    assistant_reply: str
    model_used: str = ""

    def __post_init__(self) -> None:
        self.body_markdown = strip_ai_dividers(self.body_markdown)
        self.assistant_reply = strip_ai_dividers(self.assistant_reply)


@dataclass
class RefinedEmail:
    """Chat-driven revision of a subject+body email draft (Phase 13) — the
    same "apply this instruction" shape as RefinedDocument, generalized to
    reference-request and supervisor-outreach emails."""

    subject: str
    body: str
    assistant_reply: str
    model_used: str = ""

    def __post_init__(self) -> None:
        self.body = strip_ai_dividers(self.body)
        self.assistant_reply = strip_ai_dividers(self.assistant_reply)


@dataclass
class ExtractedListing:
    """One raw listing pulled from a scraped page by the LLM."""

    title: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    research_field: Optional[str] = None
    offer_type: Optional[str] = None
    funding_info: Optional[str] = None
    deadline_text: Optional[str] = None
    contact_email: Optional[str] = None
    application_url: Optional[str] = None
    description: Optional[str] = None
    required_docs: list[str] = field(default_factory=list)
    source_key: Optional[str] = None
