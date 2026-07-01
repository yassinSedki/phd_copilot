"""Shared LLM data types. Providers return these; pipeline consumes them.

Keeping the dataclasses out of `base.py` lets call sites import the types
without pulling in the ABC's transitive deps (langchain, langgraph).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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


@dataclass
class RefinedLetter:
    body_markdown: str
    assistant_reply: str
    model_used: str


@dataclass
class EmailBody:
    subject: str
    body: str
    model_used: str


@dataclass
class ResearchSummary:
    summary: str
    overlaps: list[str]
    recent_work: list[str]
    publications: list[str] = field(default_factory=list)
    lab_url: Optional[str] = None
    model_used: str = ""


@dataclass
class OutreachDraft:
    subject: str
    body: str
    model_used: str


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
    source_key: Optional[str] = None
