"""StandardLLMClient — concrete app-level methods on top of abstract chat.

Each method below follows the same shape:
    1. Build messages from shared.llm.prompts.<task>.SYSTEM + build_user(...)
    2. Call self.invoke(messages, json_mode=...)
    3. Parse JSON
    4. Map to dataclass

Prompts live in `shared/llm/prompts/`. Tweaking a prompt is a one-file
change with no provider code touched.

Providers (Anthropic, Cohere, ...) only implement `invoke` / `ainvoke` /
`model_name`. Everything else is inherited from here.

Falls back to the stub on any `LLMError` — keeps the demo flow alive when
a provider rate-limits. Subclasses can override individual methods and
re-raise for strict behaviour.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from shared.llm.base import LLMClient, Message
from shared.llm.errors import LLMError, LLMErrorCode
from shared.llm.prompts import (
    draft_cover_letter as draft_prompt,
    draft_email_body as email_prompt,
    draft_outreach_email as outreach_prompt,
    extract_listings as extract_prompt,
    parse_listing as parse_prompt,
    refine_cover_letter as refine_prompt,
    score_listing as score_prompt,
)
from shared.llm.providers.stub import StubLLMClient
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


def _extract_json(text: str) -> Any:
    """Pull a JSON object/array out of free-form LLM output."""

    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise LLMError(LLMErrorCode.PARSE_ERROR, f"Could not parse JSON from model output: {text[:300]}")


def _messages(system: str, user: str) -> list[Message]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


class StandardLLMClient(LLMClient):
    """Concrete LLMClient on top of abstract chat. Subclasses implement
    `invoke` / `ainvoke` / `model_name`; everything else is inherited."""

    _model: str = "unknown"
    _fallback: LLMClient

    @property
    def model_name(self) -> str:
        return self._model

    def _init_fallback(self) -> None:
        self._fallback = StubLLMClient(model=self._model)

    # ---- abstract chat ----

    def invoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        raise NotImplementedError

    async def ainvoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        raise NotImplementedError

    # =========================================================================
    # Application-level helpers. Prompts come from shared.llm.prompts.*
    # =========================================================================

    def parse_listing(self, raw: str) -> ParsedListing:
        try:
            out = self.invoke(
                _messages(parse_prompt.SYSTEM, parse_prompt.build_user(raw)),
                json_mode=True,
            )
            data = _extract_json(out)
        except LLMError:
            return self._fallback.parse_listing(raw)

        deadline: Optional[datetime] = None
        deadline_raw = data.get("deadline")
        if deadline_raw:
            try:
                deadline = datetime.fromisoformat(str(deadline_raw)[:10])
            except ValueError:
                deadline = None
        if deadline is None:
            deadline = datetime.utcnow() + timedelta(days=60)

        required = data.get("required_docs") or []
        if isinstance(required, str):
            required = [d.strip() for d in required.split(",") if d.strip()]

        return ParsedListing(
            title=data.get("title"),
            institution=data.get("institution"),
            country=data.get("country"),
            city=data.get("city"),
            research_field=data.get("research_field"),
            offer_type=data.get("offer_type") or "PhD",
            funding_info=data.get("funding_info"),
            deadline=deadline,
            contact_email=data.get("contact_email"),
            application_url=data.get("application_url"),
            required_docs=list(required),
            description=data.get("description") or raw[:2000],
            parsed_ok=True,
        )

    def score_listing(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> ScoreResult:
        try:
            out = self.invoke(
                _messages(score_prompt.SYSTEM, score_prompt.build_user(profile, listing)),
                json_mode=True,
            )
            data = _extract_json(out)
        except LLMError:
            return self._fallback.score_listing(profile, listing, model=model)

        breakdown = data.get("fit_breakdown") or {}
        return ScoreResult(
            score=float(data.get("score", 0)),
            fit_breakdown={k: float(v) for k, v in breakdown.items() if isinstance(v, (int, float))},
            reasons=str(data.get("reasons") or ""),
            red_flags=[str(x) for x in (data.get("red_flags") or [])],
            model_used=model or self._model,
        )

    def draft_cover_letter(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        template: str,
        *,
        model: Optional[str] = None,
    ) -> DraftedLetter:
        try:
            body = self.invoke(
                _messages(draft_prompt.SYSTEM, draft_prompt.build_user(profile, listing, template))
            )
        except LLMError:
            return self._fallback.draft_cover_letter(profile, listing, template, model=model)
        return DraftedLetter(body_markdown=body.strip(), model_used=model or self._model)

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
        try:
            out = self.invoke(
                _messages(
                    refine_prompt.SYSTEM,
                    refine_prompt.build_user(
                        current_markdown,
                        chat_history,
                        user_message,
                        profile=profile,
                        listing=listing,
                    ),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return RefinedLetter(
                body_markdown=str(data.get("letter") or current_markdown),
                assistant_reply=str(data.get("reply") or "Updated."),
                model_used=model or self._model,
            )
        except LLMError:
            return self._fallback.refine_cover_letter(
                current_markdown,
                chat_history,
                user_message,
                profile=profile,
                listing=listing,
                model=model,
            )

    def draft_email_body(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> EmailBody:
        try:
            out = self.invoke(
                _messages(email_prompt.SYSTEM, email_prompt.build_user(profile, listing)),
                json_mode=True,
            )
            data = _extract_json(out)
            return EmailBody(
                subject=str(data.get("subject") or "Application enquiry"),
                body=str(data.get("body") or ""),
                model_used=model or self._model,
            )
        except LLMError:
            return self._fallback.draft_email_body(profile, listing, model=model)

    def draft_outreach_email(
        self,
        profile: dict[str, Any],
        research: ResearchSummary,
        *,
        model: Optional[str] = None,
    ) -> OutreachDraft:
        try:
            out = self.invoke(
                _messages(
                    outreach_prompt.SYSTEM,
                    outreach_prompt.build_user(profile, research),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return OutreachDraft(
                subject=str(data.get("subject") or "Prospective PhD enquiry"),
                body=str(data.get("body") or ""),
                model_used=model or self._model,
            )
        except LLMError:
            return self._fallback.draft_outreach_email(profile, research, model=model)

    def research_lab(
        self,
        professor: str,
        institution: Optional[str],
        topic: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ResearchSummary:
        # The deep-dive LangGraph drives the real research nodes. This leaf
        # helper just returns the stubbed summary.
        return self._fallback.research_lab(professor, institution, topic, model=model)

    def extract_listings_from_html(
        self,
        html_or_text: str,
        source_url: str,
        *,
        model: Optional[str] = None,
    ) -> list[ExtractedListing]:
        try:
            out = self.invoke(
                _messages(
                    extract_prompt.SYSTEM,
                    extract_prompt.build_user(html_or_text, source_url),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            if isinstance(data, dict) and "listings" in data:
                data = data["listings"]
            if not isinstance(data, list):
                raise LLMError(LLMErrorCode.PARSE_ERROR, "Expected JSON array")
        except LLMError:
            return self._fallback.extract_listings_from_html(html_or_text, source_url, model=model)

        results: list[ExtractedListing] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            results.append(
                ExtractedListing(
                    title=item.get("title"),
                    institution=item.get("institution"),
                    country=item.get("country"),
                    city=item.get("city"),
                    research_field=item.get("research_field"),
                    offer_type=item.get("offer_type"),
                    funding_info=item.get("funding_info"),
                    deadline_text=item.get("deadline_text") or item.get("deadline"),
                    contact_email=item.get("contact_email"),
                    application_url=item.get("application_url") or source_url,
                    description=item.get("description"),
                    source_key=item.get("source_key"),
                )
            )
        return results
