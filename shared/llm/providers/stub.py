"""Deterministic stub provider. No SDK imports, no network. Same input ->
same output. Used for offline dev, tests, and CI."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from shared.llm.base import LLMClient, Message
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


class StubLLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "stub",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: int = 60,
        json_mode: bool = False,
    ) -> None:
        self._model = model
        self._json_mode = json_mode

    @property
    def model_name(self) -> str:
        return self._model

    # ---- raw chat helpers (echo style)

    def invoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        last = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        if json_mode:
            return json.dumps({"stub": True, "echo": last[:200]})
        return f"(stub reply) {last[:200]}"

    async def ainvoke(self, messages: list[Message], *, json_mode: bool = False) -> str:
        return self.invoke(messages, json_mode=json_mode)

    # ---- application operations

    @staticmethod
    def _re(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[str]:
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else None

    def parse_listing(self, raw: str) -> ParsedListing:
        title = self._re(r"title:\s*(.+)", raw)
        institution = self._re(r"institution:\s*(.+)", raw)
        country = self._re(r"country:\s*(.+)", raw)
        city = self._re(r"city:\s*(.+)", raw)
        field_ = self._re(r"field:\s*(.+)", raw)
        offer_type = self._re(r"offer[_ ]type:\s*(.+)", raw)
        funding = self._re(r"funding:\s*(.+)", raw)
        contact = self._re(r"contact[_ ]email:\s*([\w.+-]+@[\w.-]+)", raw)
        app_url = self._re(r"application[_ ]url:\s*(\S+)", raw)
        deadline_str = self._re(r"deadline:\s*(\d{4}-\d{2}-\d{2})", raw)

        deadline: Optional[datetime] = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str)
            except ValueError:
                deadline = None
        if deadline is None:
            deadline = datetime.utcnow() + timedelta(days=60)

        docs_line = self._re(r"required[_ ]docs:\s*(.+)", raw) or ""
        required_docs = [d.strip() for d in docs_line.split(",") if d.strip()] or [
            "CV",
            "Cover Letter",
            "Transcripts",
        ]

        return ParsedListing(
            title=title or "Untitled position",
            institution=institution,
            country=country,
            city=city,
            research_field=field_,
            offer_type=offer_type or "PhD",
            funding_info=funding,
            deadline=deadline,
            contact_email=contact,
            application_url=app_url,
            required_docs=required_docs,
            description=raw[:2000],
            parsed_ok=True,
        )

    def score_listing(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> ScoreResult:
        key = f"{listing.get('title')}|{listing.get('institution')}|{listing.get('source_key')}"
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        base = digest[0] % 101

        interests = (profile.get("interests") or "").lower()
        field_text = (listing.get("research_field") or "").lower()
        bump = 0
        if interests and field_text and any(word in field_text for word in interests.split()):
            bump += 15
        if "fully funded" in (listing.get("funding_info") or "").lower():
            bump += 10
        score = max(0, min(100, base + bump))

        fit_breakdown = {
            "topic": float(min(100, base + bump)),
            "methods": float(max(0, base - 10)),
            "location": float(digest[1] % 101),
            "funding": float(80 if "fully funded" in (listing.get("funding_info") or "").lower() else 50),
            "career": float(max(0, base - 5)),
        }

        red_flags: list[str] = []
        if "unfunded" in (listing.get("funding_info") or "").lower():
            red_flags.append("Position appears unfunded.")
        if score < 30:
            red_flags.append("Topic looks far from the profile's interests.")

        return ScoreResult(
            score=float(score),
            fit_breakdown=fit_breakdown,
            reasons=(
                f"Stub scoring. Topic-field overlap bonus: {bump}. "
                "(Switch LLM__PROVIDER=anthropic for real scoring.)"
            ),
            red_flags=red_flags,
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
        full_name = (profile.get("full_name") or "Applicant").strip()
        interests = (profile.get("interests") or "the role's research area").strip()
        summary = (profile.get("research_summary") or profile.get("cv_text") or "my research work").strip()

        rendered = (
            template.replace("{{full_name}}", full_name)
            .replace("{{position_title}}", listing.get("title") or "the open position")
            .replace("{{institution}}", listing.get("institution") or "your institution")
            .replace("{{city}}", listing.get("city") or "")
            .replace("{{country}}", listing.get("country") or "")
            .replace("{{research_field}}", listing.get("research_field") or "the research area")
            .replace("{{interests}}", interests)
            .replace("{{research_summary}}", summary[:1500])
        )
        return DraftedLetter(body_markdown=rendered, model_used=model or self._model)

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
        msg = user_message.lower()
        body = current_markdown
        note = "Applied a stubbed refinement."
        if "concise" in msg or "shorter" in msg:
            lines = [ln for ln in body.splitlines() if ln.strip()]
            body = "\n".join(lines[: max(6, len(lines) // 2)])
            note = "Trimmed to roughly half length."
        elif "less formal" in msg or "casual" in msg:
            body = body.replace("Sincerely,", "Best,").replace("Dear Hiring Committee,", "Hi,")
            note = "Loosened the tone."
        elif "formal" in msg:
            body = body.replace("Hi,", "Dear Hiring Committee,").replace("Best,", "Sincerely,")
            note = "Tightened the tone."
        elif user_message.strip():
            body = body + f"\n\n_Edit: {user_message.strip()}_\n"
            note = "Appended your instruction as a note."

        return RefinedLetter(
            body_markdown=body,
            assistant_reply=note,
            model_used=model or self._model,
        )

    def draft_outreach_email(
        self,
        profile: dict[str, Any],
        research: ResearchSummary,
        *,
        model: Optional[str] = None,
    ) -> OutreachDraft:
        full_name = (profile.get("full_name") or "[Your name]").strip()
        interests = (profile.get("interests") or "your area of research").strip()
        subject = "Prospective PhD enquiry: research overlap and possible collaboration"
        body = (
            "Dear Professor,\n\n"
            f"I came across your group's recent work and was struck by "
            f"{research.recent_work[0] if research.recent_work else 'your recent publications'}. "
            f"My own background centres on {interests}, which connects to "
            f"{research.overlaps[0] if research.overlaps else 'your line of research'}.\n\n"
            "I would be very grateful to learn whether you are accepting PhD applicants "
            "for the coming cycle, and where my profile could be most useful.\n\n"
            f"With many thanks,\n{full_name}\n"
        )
        return OutreachDraft(subject=subject, body=body, model_used=model or self._model)

    def draft_email_body(
        self,
        profile: dict[str, Any],
        listing: dict[str, Any],
        *,
        model: Optional[str] = None,
    ) -> EmailBody:
        full_name = (profile.get("full_name") or "[Your name]").strip()
        title = listing.get("title") or "the open position"
        institution = listing.get("institution") or "your group"
        body = (
            "Dear Sir or Madam,\n\n"
            f"I am writing to express interest in {title} at {institution}. "
            "I have attached my CV and a short cover letter; happy to share further "
            "materials if helpful.\n\n"
            f"Kind regards,\n{full_name}\n"
        )
        return EmailBody(
            subject=f"Application enquiry — {title}",
            body=body,
            model_used=model or self._model,
        )

    def research_lab(
        self,
        professor: str,
        institution: Optional[str],
        topic: Optional[str],
        *,
        model: Optional[str] = None,
    ) -> ResearchSummary:
        inst = institution or "their institution"
        topic_clean = topic or "their field"
        return ResearchSummary(
            summary=(
                f"{professor} at {inst} appears to focus on {topic_clean}. "
                "Stubbed deep-dive: recent activity suggests experimental work, "
                "computational modelling, and collaborative projects with related groups."
            ),
            overlaps=[
                f"Shared interest in {topic_clean}.",
                "Methodology overlap: data-driven analysis and instrument design.",
                "Possible collaboration angle on open-source tooling.",
            ],
            recent_work=[
                f"Paper on {topic_clean} dynamics (stubbed).",
                "Recent talk at a community workshop (stubbed).",
                "Active grant in the area (stubbed).",
            ],
            publications=[],
            lab_url=None,
            model_used=model or self._model,
        )

    def extract_listings_from_html(
        self,
        html_or_text: str,
        source_url: str,
        *,
        model: Optional[str] = None,
    ) -> list[ExtractedListing]:
        """Deterministic stub: pulls "title:" blocks if present, otherwise
        returns a single shaped listing derived from the URL hash. Lets the
        scraper graph run end-to-end without a real LLM."""

        blocks = re.split(r"\n\s*\n", html_or_text)
        results: list[ExtractedListing] = []
        for i, block in enumerate(blocks):
            title = self._re(r"title:\s*(.+)", block)
            if not title:
                continue
            results.append(
                ExtractedListing(
                    title=title,
                    institution=self._re(r"institution:\s*(.+)", block),
                    country=self._re(r"country:\s*(.+)", block),
                    city=self._re(r"city:\s*(.+)", block),
                    research_field=self._re(r"field:\s*(.+)", block),
                    offer_type=self._re(r"offer[_ ]type:\s*(.+)", block),
                    funding_info=self._re(r"funding:\s*(.+)", block),
                    deadline_text=self._re(r"deadline:\s*(.+)", block),
                    contact_email=self._re(r"contact[_ ]email:\s*([\w.+-]+@[\w.-]+)", block),
                    application_url=self._re(r"application[_ ]url:\s*(\S+)", block),
                    description=block[:2000],
                    source_key=f"{hashlib.sha256(source_url.encode()).hexdigest()[:12]}-{i}",
                )
            )

        if not results:
            digest = hashlib.sha256(f"{source_url}|{html_or_text[:500]}".encode()).hexdigest()
            results.append(
                ExtractedListing(
                    title=f"Stub listing extracted from {source_url[:60]}",
                    institution="Unknown",
                    country="Unknown",
                    research_field="general research",
                    offer_type="PhD",
                    funding_info="Unknown",
                    deadline_text=(datetime.utcnow() + timedelta(days=45)).date().isoformat(),
                    application_url=source_url,
                    description=html_or_text[:1500],
                    source_key=digest[:12],
                )
            )
        return results
