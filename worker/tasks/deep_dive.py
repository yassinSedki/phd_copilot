"""deep_dive task. Architecture: phd copilot.md → Deep Dive agent.

Drives `research_graph.run_deep_dive_graph` and persists the result as a
Contact + Outreach row. The contact's `email` field stays NULL — section
"Hard rules": only manually-confirmed emails are stored, the user fills
it in via PATCH /api/outreach/:id before sending.
"""

from __future__ import annotations

import asyncio
import traceback

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.database import SessionLocal
from shared.models import Contact, Outreach
from shared.repositories import jobs as jobs_repo
from shared.repositories import users as users_repo
from worker.pipeline.deepdive.research_graph import run_deep_dive_graph
from shared.llm import get_llm


def _profile_payload(profile) -> dict:
    if profile is None:
        return {}
    return {
        "full_name": profile.full_name,
        "research_summary": profile.research_summary,
        "interests": profile.interests,
        "cv_text": (profile.cv_text or "")[:6000],
    }


async def _run_async(
    user_id: int,
    job_id: int,
    *,
    professor_name: str,
    institution: str | None,
    lab_url: str | None,
    topic: str | None,
    personal_note: str | None = None,
) -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        jobs_repo.mark_running(db, job_id)
        profile = users_repo.get_profile(db, user_id)
        llm = get_llm(settings.llm, role="researcher")

        jobs_repo.update_progress(db, job_id, 20)

        def on_step(label: str, pct: int) -> None:
            # Streamed to the UI: the agent's real process, not an animation.
            jobs_repo.update_progress(db, job_id, pct, meta={"current_step": label})

        final = await run_deep_dive_graph(
            professor_name=professor_name,
            institution=institution,
            topic=topic,
            lab_url=lab_url,
            user_profile=_profile_payload(profile),
            llm=llm,
            user_agent=settings.scraper_user_agent,
            personal_note=personal_note,
            on_step=on_step,
        )
        jobs_repo.update_progress(db, job_id, 90, meta={"current_step": "Saving the dossier"})

        researched = bool(final.get("research_topics") or final.get("publications"))
        source_note_lines = (
            ["Topics:"] + [f"- {x}" for x in final.get("research_topics") or []]
            + ["", "Publications:"] + [f"- {x}" for x in final.get("publications") or []]
            + ["", "Overlaps:"] + [f"- {x}" for x in final.get("overlap_points") or []]
        )
        if not researched:
            # Be honest rather than fabricate: no verified lab page was found,
            # so the draft is based only on the user's own inputs.
            source_note_lines = [
                "No lab page could be found or verified for this professor.",
                "The draft email is based only on your profile and the details you entered.",
                "Add a lab URL and re-run the research for a cited, specific email.",
            ]

        contact = Contact(
            user_id=user_id,
            professor_name=professor_name,
            institution=institution,
            lab_url=final.get("lab_url"),
            email=None,  # HARD RULE — never auto-store
            research_summary=final.get("summary_text") or "",
            publications=[{"title": p} for p in (final.get("publications") or [])],
            source_notes="\n".join(source_note_lines),
        )
        db.add(contact)
        db.flush()

        subject = final.get("email_subject") or "Prospective PhD enquiry"
        body = final.get("email_draft") or ""
        outreach = Outreach(
            user_id=user_id,
            contact_id=contact.id,
            draft_email=f"Subject: {subject}\n\n{body}",
            email_subject=subject,
            email_body=body,
            status="DRAFT",
            chat_history=[],
        )
        db.add(outreach)
        db.commit()

        jobs_repo.mark_done(
            db,
            job_id,
            result_ref=f"outreach_id={outreach.id} contact_id={contact.id} quality={final.get('quality')}",
        )
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
    finally:
        db.close()


def deep_dive(
    user_id: int,
    job_id: int,
    *,
    professor_name: str,
    institution: str | None = None,
    lab_url: str | None = None,
    topic: str | None = None,
    personal_note: str | None = None,
) -> None:
    """Sync entry for FastAPI BackgroundTasks."""

    kwargs = dict(
        professor_name=professor_name,
        institution=institution,
        lab_url=lab_url,
        topic=topic,
        personal_note=personal_note,
    )
    try:
        asyncio.run(_run_async(user_id, job_id, **kwargs))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run_async(user_id, job_id, **kwargs))
        finally:
            loop.close()
