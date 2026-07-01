"""LLMClient ABC. Thin interface — providers handle keys, retries, JSON mode.

Factory guide §9 — keep the ABC minimal; do not leak provider-specific
parameters here. Messages use the OpenAI-style dict list which Anthropic +
Cohere + OpenAI all support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from shared.llm.types import (
    DraftedLetter,
    EmailBody,
    ExtractedListing,
    OutreachDraft,
    ParsedListing,
    RefinedLetter,
    ResearchSummary,
    ScoreResult,
)


Message = dict[str, str]


class LLMClient(ABC):
    """Abstract base. Two raw chat methods + the application-specific helpers
    that all providers implement on top of them.

    Subclasses MUST implement `invoke` / `ainvoke` and `model_name`. The
    higher-level helpers (parse_listing, score_listing, ...) have default
    implementations that compose chat prompts — providers may override for
    structured output mode (json_object, tool use) when their SDK supports
    it natively.
    """

    @abstractmethod
    def invoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        ...

    @abstractmethod
    async def ainvoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    # ---- Application-specific operations. Providers MUST implement.

    @abstractmethod
    def parse_listing(self, raw: str) -> ParsedListing:
        ...

    @abstractmethod
    def score_listing(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> ScoreResult:
        ...

    @abstractmethod
    def draft_cover_letter(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        template: str,
        *,
        model: Optional[str] = None,
    ) -> DraftedLetter:
        ...

    @abstractmethod
    def refine_cover_letter(
        self,
        current_markdown: str,
        chat_history: list[Message],
        user_message: str,
        *,
        profile: dict[str, Any],
        listing: dict[str, Any],
        model: Optional[str] = None,
    ) -> RefinedLetter:
        ...

    @abstractmethod
    def draft_outreach_email(
        self,
        profile: dict[str, Any],
        research: ResearchSummary,
        *,
        model: Optional[str] = None,
    ) -> OutreachDraft:
        ...

    @abstractmethod
    def draft_email_body(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> EmailBody:
        ...

    @abstractmethod
    def research_lab(
        self,
        professor: str,
        institution: Optional[str],
        topic: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ResearchSummary:
        ...

    @abstractmethod
    def extract_listings_from_html(
        self,
        html_or_text: str,
        source_url: str,
        *,
        model: Optional[str] = None,
    ) -> list[ExtractedListing]:
        ...
