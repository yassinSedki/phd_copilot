"""Cover-letter service. Generates the initial letter, refines it via chat,
and produces the outreach email body. All three operations go through the
LLM factory so providers can be swapped via .env.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from shared.config import get_settings
from shared.models import Application, CoverLetter, Listing, Profile
from shared.models.base import utcnow
from shared.services import state_machine as sm
from shared.llm import EmailBody, LLMClient, get_llm

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "worker" / "pipeline" / "draft" / "templates" / "cover_letter.md"


def _profile_payload(profile: Profile | None) -> dict:
    if profile is None:
        return {}
    return {
        "full_name": profile.full_name,
        "research_summary": profile.research_summary,
        "interests": profile.interests,
        "skills": profile.skills,
        "languages": profile.languages,
        "publications": profile.publications,
        "cv_text": (profile.cv_text or "")[:8000],
        "cv_filename": profile.cv_filename,
    }


def _listing_payload(listing: Listing) -> dict:
    return {
        "title": listing.title,
        "institution": listing.institution,
        "country": listing.country,
        "city": listing.city,
        "research_field": listing.research_field,
        "description": listing.description,
        "funding_info": listing.funding_info,
    }


def _get_or_create_cover_letter(db: Session, application: Application) -> CoverLetter:
    existing = db.scalar(select(CoverLetter).where(CoverLetter.application_id == application.id))
    if existing is not None:
        return existing
    cover = CoverLetter(
        user_id=application.user_id,
        application_id=application.id,
        body_markdown=None,
        chat_history=[],
    )
    db.add(cover)
    db.flush()
    return cover


def get_letter(db: Session, application: Application) -> Optional[CoverLetter]:
    return db.scalar(select(CoverLetter).where(CoverLetter.application_id == application.id))


def generate_initial(
    db: Session,
    application: Application,
    profile: Profile | None,
) -> CoverLetter:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    settings = get_settings()
    llm: LLMClient = get_llm(settings.llm, role="drafter")

    drafted = llm.draft_cover_letter(_profile_payload(profile), _listing_payload(application.listing), template)

    cover = _get_or_create_cover_letter(db, application)
    cover.body_markdown = drafted.body_markdown
    cover.chat_history = [
        {"role": "assistant", "content": "Initial draft generated from your CV and the listing.", "at": utcnow().isoformat()}
    ]
    cover.model_used = drafted.model_used
    cover.updated_at = utcnow()

    if application.status == sm.SAVED:
        application.status = sm.IN_PROGRESS

    application.cover_letter_path = None  # the body lives in the DB now
    db.flush()
    return cover


def refine_via_chat(
    db: Session,
    application: Application,
    profile: Profile | None,
    user_message: str,
) -> tuple[CoverLetter, str]:
    cover = _get_or_create_cover_letter(db, application)
    if not cover.body_markdown:
        # generate initial if missing — first chat turn doubles as draft
        cover = generate_initial(db, application, profile)

    settings = get_settings()
    llm: LLMClient = get_llm(settings.llm, role="refiner")

    history = list(cover.chat_history or [])
    refined = llm.refine_cover_letter(
        cover.body_markdown or "",
        [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history],
        user_message,
        profile=_profile_payload(profile),
        listing=_listing_payload(application.listing),
    )

    history.append({"role": "user", "content": user_message, "at": utcnow().isoformat()})
    history.append({"role": "assistant", "content": refined.assistant_reply, "at": utcnow().isoformat()})

    cover.body_markdown = refined.body_markdown
    cover.chat_history = history
    cover.model_used = refined.model_used
    cover.updated_at = utcnow()
    db.flush()
    return cover, refined.assistant_reply


def draft_email(
    db: Session,
    application: Application,
    profile: Profile | None,
) -> EmailBody:
    settings = get_settings()
    llm: LLMClient = get_llm(settings.llm, role="drafter")
    email = llm.draft_email_body(_profile_payload(profile), _listing_payload(application.listing))

    cover = _get_or_create_cover_letter(db, application)
    cover.email_subject = email.subject
    cover.email_body = email.body
    cover.model_used = email.model_used
    cover.updated_at = utcnow()
    db.flush()
    return email
