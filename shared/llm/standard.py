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

import logging
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Optional

from shared.llm.base import LLMClient, Message
from shared.llm.errors import LLMError, LLMErrorCode
from shared.llm.prompts import (
    draft_cover_letter as draft_prompt,
    draft_document as draft_document_prompt,
    draft_email_body as email_prompt,
    draft_outreach_email as outreach_prompt,
    draft_reference_followup as reference_followup_prompt,
    draft_reference_request as reference_request_prompt,
    explain_fit as explain_fit_prompt,
    extract_listing_detail as extract_detail_prompt,
    extract_listings as extract_prompt,
    extract_profile_from_cv as extract_profile_prompt,
    parse_listing as parse_prompt,
    refine_cover_letter as refine_prompt,
    refine_document as refine_document_prompt,
    refine_email as refine_email_prompt,
    score_listing as score_prompt,
)
from shared.llm.providers.stub import StubLLMClient
from shared.llm.scoring import compute_fit_score
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


log = logging.getLogger("phd_copilot.llm")


# The shared implementation lives in jsonx.py so non-client code (prefilter,
# deep-dive nodes) uses the same robust parser instead of bare json.loads.
from shared.llm.jsonx import extract_json as _extract_json  # noqa: E402


def _messages(system: str, user: str) -> list[Message]:
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _looks_like_url(value: object) -> bool:
    """Reject values that are a truncated/ellipsized display string rather
    than a real URL — e.g. a model that echoes a UI's "…"-truncated link
    text instead of resolving the actual href. A corrupted URL here is worse
    than none: it silently overwrites the hint's real, DOM-derived link."""
    if not isinstance(value, str) or not value:
        return False
    if "…" in value or value.rstrip().endswith("..."):
        return False
    return bool(re.match(r"^https?://[^\s]+$", value.strip()))


_EMAIL_MARKDOWN_RE = re.compile(r"\*\*([^*]+)\*\*|(?<!\w)\*([^*\n]+)\*(?!\w)")
_EMAIL_HEADER_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)


def _strip_email_markdown(text: str) -> str:
    """These are plain-text emails, never rendered through a markdown-to-
    HTML pass — the prompt tells the model not to bold/header anything, but
    models don't reliably follow that, so this is the code-side backstop:
    unwrap **bold**/*italic* to their plain text and drop leading #headers."""
    text = _EMAIL_MARKDOWN_RE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    return _EMAIL_HEADER_RE.sub("", text)


def _clean_required_docs(raw: object) -> list[str]:
    """Normalize the model's required_docs into a clean list of submission
    documents. Splits comma-mashed strings and drops long entries — a
    "document" over ~80 chars is nearly always an eligibility/requirements
    sentence the prompt told the model to keep out, not a document name."""
    if isinstance(raw, str):
        items: list[object] = [d for d in raw.split(",")]
    elif isinstance(raw, list):
        items = raw
    else:
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        doc = str(item).strip().strip("-–•· ").rstrip(".")
        if not doc or len(doc) > 80:
            continue
        key = doc.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(doc)
    return cleaned


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

    def _fallback_warn(self, method: str, exc: LLMError) -> None:
        # This is the single most important log line for "why did I get a
        # fabricated/generic result" — every app-level method silently used
        # to swallow LLMError and hand back the deterministic stub with zero
        # trace. Now it says exactly which call failed and why.
        log.warning(
            "%s: %s (%s) fell back to stub — real result unavailable this call",
            method,
            exc,
            self.model_name,
        )

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
        except LLMError as exc:
            self._fallback_warn("parse_listing", exc)
            return self._fallback.parse_listing(raw)

        # No deadline on the page means NO deadline — fabricating "+60 days"
        # here used to flow into reminders/urgency as if it were real.
        deadline: Optional[datetime] = None
        deadline_raw = data.get("deadline")
        if deadline_raw:
            try:
                deadline = datetime.fromisoformat(str(deadline_raw)[:10])
            except ValueError:
                deadline = None
        # Sanity: extraction bugs concentrate in dates — a deadline more
        # than 2 years out is almost certainly a mis-parse.
        if deadline is not None and deadline > datetime.utcnow() + timedelta(days=730):
            deadline = None

        required = _clean_required_docs(data.get("required_docs"))

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
            application_url=data.get("application_url") if _looks_like_url(data.get("application_url")) else None,
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
            today = datetime.utcnow().date().isoformat()
            out = self.invoke(
                _messages(score_prompt.SYSTEM, score_prompt.build_user(profile, listing, today)),
                json_mode=True,
            )
            data = _extract_json(out)
        except LLMError as exc:
            self._fallback_warn("score_listing", exc)
            return self._fallback.score_listing(profile, listing, model=model)

        rubric_raw = data.get("rubric") or {}
        flags = data.get("flags") or {}
        red_flags = [str(x) for x in (data.get("red_flags") or [])]

        if not rubric_raw:
            # Model ignored the rubric contract — salvage a legacy-shaped
            # answer rather than scoring the listing 0.
            breakdown = data.get("fit_breakdown") or {}
            return ScoreResult(
                score=float(data.get("score", 0)),
                fit_breakdown={k: float(v) for k, v in breakdown.items() if isinstance(v, (int, float))},
                reasons=str(data.get("reasons") or data.get("justification") or ""),
                red_flags=red_flags,
                model_used=model or self._model,
            )

        # The code, not the model, owns the total (AGENT.md §3.7): clamp,
        # sum and hard-fail caps live in a pure, unit-tested function.
        total, rubric, cap_flags = compute_fit_score(
            rubric_raw, flags, str(profile.get("constraints") or "")
        )
        red_flags.extend(cap_flags)

        # Store the breakdown normalized to /100 per dimension so UI bars
        # remain comparable across dimensions with different rubric weights.
        result = ScoreResult(
            score=total,
            fit_breakdown={
                k.replace("_", " "): round(v / score_prompt.RUBRIC_MAX[k] * 100)
                for k, v in rubric.items()
            },
            reasons=str(data.get("justification") or data.get("reasons") or ""),
            red_flags=red_flags,
            model_used=model or self._model,
        )
        log.info(
            "score_listing: %r -> %.0f (breakdown=%s, red_flags=%s)",
            listing.get("title"),
            result.score,
            result.fit_breakdown,
            result.red_flags,
        )
        return result

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
        except LLMError as exc:
            self._fallback_warn("draft_cover_letter", exc)
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
        except LLMError as exc:
            self._fallback_warn("refine_cover_letter", exc)
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
        except LLMError as exc:
            self._fallback_warn("draft_email_body", exc)
            return self._fallback.draft_email_body(profile, listing, model=model)

    def draft_outreach_email(
        self,
        profile: dict[str, Any],
        research: ResearchSummary,
        *,
        personal_note: Optional[str] = None,
        model: Optional[str] = None,
    ) -> OutreachDraft:
        try:
            out = self.invoke(
                _messages(
                    outreach_prompt.SYSTEM,
                    outreach_prompt.build_user(profile, research, personal_note),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return OutreachDraft(
                subject=_strip_email_markdown(str(data.get("subject") or "Prospective PhD enquiry")),
                body=_strip_email_markdown(str(data.get("body") or "")),
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("draft_outreach_email", exc)
            return self._fallback.draft_outreach_email(profile, research, personal_note=personal_note, model=model)

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
            if isinstance(data, dict):
                # Providers whose JSON mode only guarantees a top-level
                # object (e.g. Cohere's response_format=json_object) can't
                # return a bare array even if asked to — accept whichever
                # key the model actually used for the array.
                for key in ("listings", "jobs", "results", "items", "data"):
                    if isinstance(data.get(key), list):
                        data = data[key]
                        break
            if not isinstance(data, list):
                shape = list(data.keys()) if isinstance(data, dict) else type(data).__name__
                raise LLMError(LLMErrorCode.PARSE_ERROR, f"Expected JSON array, got {shape}")
        except LLMError as exc:
            self._fallback_warn("extract_listings_from_html", exc)
            fallback_results = self._fallback.extract_listings_from_html(html_or_text, source_url, model=model)
            log.warning(
                "extract_listings_from_html: real extraction failed for %s — using %d stub-synthesized listing(s) "
                "instead of parsing the real page. This is why a listing title can look like "
                "'Stub listing extracted from <url>' instead of the real title.",
                source_url,
                len(fallback_results),
            )
            return fallback_results

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
                    application_url=item.get("application_url") if _looks_like_url(item.get("application_url")) else source_url,
                    description=item.get("description"),
                    source_key=item.get("source_key"),
                )
            )
        log.info("extract_listings_from_html: %s -> %d real listing(s) parsed", source_url, len(results))
        return results

    def extract_listing_detail(
        self,
        hint: ExtractedListing,
        detail_text: str,
        source_url: str,
        *,
        model: Optional[str] = None,
    ) -> ExtractedListing:
        hint_dict = asdict(hint)
        try:
            out = self.invoke(
                _messages(extract_detail_prompt.SYSTEM, extract_detail_prompt.build_user(hint_dict, detail_text, source_url)),
                json_mode=True,
            )
            data = _extract_json(out)
            if not isinstance(data, dict):
                raise LLMError(LLMErrorCode.PARSE_ERROR, f"Expected JSON object, got {type(data).__name__}")
        except LLMError as exc:
            self._fallback_warn("extract_listing_detail", exc)
            return self._fallback.extract_listing_detail(hint, detail_text, source_url, model=model)

        required = _clean_required_docs(data.get("required_docs"))

        enriched = ExtractedListing(
            title=data.get("title") or hint.title,
            institution=data.get("institution") or hint.institution,
            country=data.get("country") or hint.country,
            city=data.get("city") or hint.city,
            research_field=data.get("research_field") or hint.research_field,
            offer_type=data.get("offer_type") or hint.offer_type,
            funding_info=data.get("funding_info") or hint.funding_info,
            deadline_text=data.get("deadline_text") or hint.deadline_text,
            contact_email=data.get("contact_email") or hint.contact_email,
            application_url=(
                data.get("application_url")
                if _looks_like_url(data.get("application_url"))
                else (hint.application_url or source_url)
            ),
            description=data.get("description") or hint.description,
            required_docs=[str(d) for d in required] or hint.required_docs,
            source_key=hint.source_key,
        )
        log.info(
            "extract_listing_detail: %r enriched from %s (funding=%r, field=%r, deadline=%r)",
            enriched.title, source_url, enriched.funding_info, enriched.research_field, enriched.deadline_text,
        )
        return enriched

    def extract_profile_from_cv(
        self,
        cv_text: str,
        *,
        model: Optional[str] = None,
    ) -> ExtractedProfile:
        try:
            out = self.invoke(
                _messages(extract_profile_prompt.SYSTEM, extract_profile_prompt.build_user(cv_text)),
                json_mode=True,
            )
            data = _extract_json(out)
        except LLMError as exc:
            self._fallback_warn("extract_profile_from_cv", exc)
            return self._fallback.extract_profile_from_cv(cv_text, model=model)

        publications = [p for p in (data.get("publications") or []) if isinstance(p, dict)][:5]

        return ExtractedProfile(
            full_name=data.get("full_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            research_summary=data.get("research_summary"),
            research_areas=[str(x) for x in (data.get("research_areas") or [])][:8],
            methods=[str(x) for x in (data.get("methods") or [])][:8],
            programming_languages=[str(x) for x in (data.get("programming_languages") or [])],
            degree_subject=data.get("degree_subject"),
            graduation_year=int(data["graduation_year"]) if data.get("graduation_year") else None,
            career_stage=data.get("career_stage"),
            languages_spoken=[str(x) for x in (data.get("languages_spoken") or [])],
            publications=publications,
            geographic_hints=[str(x) for x in (data.get("geographic_hints") or [])],
        )

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
        try:
            out = self.invoke(
                _messages(
                    draft_document_prompt.SYSTEM,
                    draft_document_prompt.build_user(profile, listing, template, doc_type, red_flags),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            body = str(data.get("body_markdown") or "").strip()
            if not body:
                raise LLMError(LLMErrorCode.PARSE_ERROR, "empty body_markdown")
            return DraftedDocument(
                body_markdown=body,
                author_notes=str(data.get("author_notes") or ""),
                warnings=[str(w) for w in (data.get("warnings") or [])],
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("draft_document", exc)
            return self._fallback.draft_document(profile, listing, template, doc_type, red_flags, model=model)

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
        try:
            out = self.invoke(
                _messages(
                    refine_document_prompt.SYSTEM,
                    refine_document_prompt.build_user(
                        doc_type, current_body, chat_history, user_message, profile=profile, listing=listing
                    ),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return RefinedDocument(
                body_markdown=str(data.get("body_markdown") or current_body),
                assistant_reply=str(data.get("reply") or "Updated."),
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("refine_document", exc)
            return self._fallback.refine_document(
                doc_type, current_body, chat_history, user_message, profile=profile, listing=listing, model=model
            )

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
        try:
            out = self.invoke(
                _messages(
                    refine_email_prompt.SYSTEM,
                    refine_email_prompt.build_user(
                        kind, current_subject, current_body, chat_history, user_message, context=context
                    ),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return RefinedEmail(
                subject=_strip_email_markdown(str(data.get("subject") or current_subject)),
                body=_strip_email_markdown(str(data.get("body") or current_body)),
                assistant_reply=str(data.get("reply") or "Updated."),
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("refine_email", exc)
            return self._fallback.refine_email(
                kind, current_subject, current_body, chat_history, user_message, context=context, model=model
            )

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
        try:
            out = self.invoke(
                _messages(
                    reference_request_prompt.SYSTEM,
                    reference_request_prompt.build_user(
                        referee, student, position, deadline, submission_method, personal_note
                    ),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return ReferenceEmailDraft(
                subject=_strip_email_markdown(str(data.get("subject") or "Reference letter request")),
                body=_strip_email_markdown(str(data.get("body") or "")),
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("draft_reference_request", exc)
            return self._fallback.draft_reference_request(
                referee, student, position, deadline, submission_method, personal_note, model=model
            )

    def draft_reference_followup(
        self,
        referee: dict[str, Any],
        position: dict[str, Any],
        sent_at: Optional[str],
        due_at: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ReferenceEmailDraft:
        try:
            out = self.invoke(
                _messages(
                    reference_followup_prompt.SYSTEM,
                    reference_followup_prompt.build_user(referee, position, sent_at, due_at),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            return ReferenceEmailDraft(
                subject=_strip_email_markdown(str(data.get("subject") or "Following up — reference letter")),
                body=_strip_email_markdown(str(data.get("body") or "")),
                model_used=model or self._model,
            )
        except LLMError as exc:
            self._fallback_warn("draft_reference_followup", exc)
            return self._fallback.draft_reference_followup(referee, position, sent_at, due_at, model=model)

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
        try:
            out = self.invoke(
                _messages(
                    explain_fit_prompt.SYSTEM,
                    explain_fit_prompt.build_user(profile, listing, breakdown, reasons, red_flags),
                ),
                json_mode=True,
            )
            data = _extract_json(out)
            paragraph = str(data.get("paragraph") or "").strip()
            if not paragraph:
                log.warning("explain_fit: model returned an empty paragraph — using stub instead")
                return self._fallback.explain_fit(profile, listing, breakdown, reasons, red_flags, model=model)
            return paragraph
        except LLMError as exc:
            self._fallback_warn("explain_fit", exc)
            return self._fallback.explain_fit(profile, listing, breakdown, reasons, red_flags, model=model)
