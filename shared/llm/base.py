"""LLMClient ABC. Thin interface — providers handle keys, retries, JSON mode.

Factory guide §9 — keep the ABC minimal; do not leak provider-specific
parameters here. Messages use the OpenAI-style dict list which Anthropic +
Cohere + OpenAI all support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from shared.llm.types import (
    DraftedDocument,
    DraftedLetter,
    EmailBody,
    ExtractedListing,
    ExtractedProfile,
    OutreachDraft,
    ParsedListing,
    ReferenceEmailDraft,
    RefinedDocument,
    RefinedEmail,
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
        personal_note: Optional[str] = None,
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

    @abstractmethod
    def extract_listing_detail(
        self,
        hint: ExtractedListing,
        detail_text: str,
        source_url: str,
        *,
        model: Optional[str] = None,
    ) -> ExtractedListing:
        """Re-extract/enrich one listing from its own dedicated page. `hint`
        is the (possibly incomplete/noisy) card extracted from the crowded
        search-results page; the detail page is authoritative."""
        ...

    @abstractmethod
    def extract_profile_from_cv(
        self,
        cv_text: str,
        *,
        model: Optional[str] = None,
    ) -> ExtractedProfile:
        ...

    @abstractmethod
    def draft_document(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        template: str,
        doc_type: str,
        red_flags: list[str],
        *,
        model: Optional[str] = None,
    ) -> DraftedDocument:
        ...

    @abstractmethod
    def refine_document(
        self,
        doc_type: str,
        current_body: str,
        chat_history: list[Message],
        user_message: str,
        *,
        profile: dict[str, Any],
        listing: dict[str, Any],
        model: Optional[str] = None,
    ) -> RefinedDocument:
        ...

    @abstractmethod
    def draft_reference_request(
        self,
        referee: dict[str, Any],
        student: dict[str, Any],
        position: dict[str, Any],
        deadline: Optional[str],
        submission_method: str,
        personal_note: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ReferenceEmailDraft:
        ...

    @abstractmethod
    def draft_reference_followup(
        self,
        referee: dict[str, Any],
        position: dict[str, Any],
        sent_at: Optional[str],
        due_at: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ReferenceEmailDraft:
        ...

    @abstractmethod
    def refine_email(
        self,
        kind: str,
        current_subject: str,
        current_body: str,
        chat_history: list[Message],
        user_message: str,
        *,
        context: dict[str, Any],
        model: Optional[str] = None,
    ) -> RefinedEmail:
        """Chat-driven revision of a reference-request or supervisor-outreach
        email draft. `kind` is "reference_request" | "supervisor_outreach";
        `context` carries whatever the caller already has (referee/professor,
        position, profile) to keep the revision grounded."""
        ...

    @abstractmethod
    def explain_fit(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        breakdown: dict[str, Any],
        reasons: str,
        red_flags: list[str],
        *,
        model: Optional[str] = None,
    ) -> str:
        ...
