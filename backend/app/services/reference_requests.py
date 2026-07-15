"""Reference-request business logic (Phase 12): drafting, creating,
marking sent (copy-to-clipboard), follow-ups, and flipping the matching
checklist item to ready when a letter is marked received.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from shared.config import get_settings
from shared.models import Application, Profile, Referee, ReferenceRequest, User
from shared.models.base import utcnow
from shared.repositories import referees as referee_repo
from shared.repositories import reference_requests as request_repo
from shared.llm import get_llm

FOLLOW_UP_DAYS_BEFORE_DUE = 10


def update_draft(db: Session, request: ReferenceRequest, *, subject: Optional[str], body: Optional[str]) -> None:
    """The user writing their own change directly, as opposed to asking the
    AI (see refine_draft below)."""
    if subject is not None:
        request.email_subject = subject
    if body is not None:
        request.email_body = body
    db.commit()


def refine_draft(
    db: Session,
    request: ReferenceRequest,
    referee: Referee,
    application: Application,
    profile: Optional[Profile],
    user_message: str,
) -> str:
    """Ask the AI to revise the current draft via chat instruction. Returns
    the assistant's one-sentence description of what changed."""
    settings = get_settings()
    llm = get_llm(settings.llm, role="refiner")

    history = list(request.chat_history or [])
    refined = llm.refine_email(
        "reference_request",
        request.email_subject or "",
        request.email_body or "",
        [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history],
        user_message,
        context={
            "referee": referee_payload(referee),
            "student": _student_payload(profile),
            "position": _position_payload(application),
            "submission_method": request.submission_method,
        },
    )

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": refined.assistant_reply})

    request.email_subject = refined.subject
    request.email_body = refined.body
    request.chat_history = history
    db.commit()
    return refined.assistant_reply


def _student_payload(profile: Optional[Profile]) -> dict:
    if profile is None:
        return {}
    return {"full_name": profile.full_name, "research_summary": profile.research_summary}


def _position_payload(application: Application) -> dict:
    listing = application.listing
    return {"title": listing.title, "institution": listing.institution}


def referee_payload(referee: Referee) -> dict:
    return {"name": referee.name, "title": referee.title, "institution": referee.institution}


def referee_payload_from_fields(name: Optional[str], title: Optional[str]) -> dict:
    return {"name": name, "title": title, "institution": None}


def get_or_create_referee(
    db: Session,
    user_id: int,
    *,
    referee_id: Optional[int],
    name: Optional[str],
    title: Optional[str],
    email: Optional[str],
) -> Referee:
    if referee_id is not None:
        referee = referee_repo.get(db, referee_id, user_id)
        if referee is not None:
            return referee
    if not name or not email:
        raise ValueError("referee_id, or name + email, is required")
    existing = db.scalar(select(Referee).where(Referee.user_id == user_id, Referee.email == email))
    if existing is not None:
        return existing
    return referee_repo.create(db, user_id, name=name, title=title, email=email)


def draft_preview(
    db: Session,
    application: Application,
    profile: Optional[Profile],
    referee_payload: dict,
    submission_method: str,
    personal_note: Optional[str],
) -> tuple[str, str]:
    settings = get_settings()
    llm = get_llm(settings.llm, role="drafter")
    draft = llm.draft_reference_request(
        referee_payload,
        _student_payload(profile),
        _position_payload(application),
        application.deadline.isoformat() if application.deadline else None,
        submission_method,
        personal_note,
    )
    return draft.subject, draft.body


def create_request(
    db: Session,
    user_id: int,
    *,
    referee: Referee,
    application: Application,
    submission_method: str,
    subject: str,
    body: str,
) -> ReferenceRequest:
    due_at = application.deadline
    follow_up_at = None
    if due_at is not None:
        from datetime import timedelta

        follow_up_at = due_at - timedelta(days=FOLLOW_UP_DAYS_BEFORE_DUE)

    return request_repo.create(
        db,
        user_id,
        referee_id=referee.id,
        application_id=application.id,
        status="draft",
        submission_method=submission_method,
        email_subject=subject,
        email_body=body,
        due_at=due_at,
        follow_up_at=follow_up_at,
    )


def _flip_checklist_item(application: Application, request_id: int) -> bool:
    """Mirrors shared/services/applications.update_docs_item but scoped to
    the one item whose reference_request_id matches — returns True if it
    changed anything."""

    items = list(application.docs_checklist or [])
    changed = False
    for item in items:
        if item.get("kind") == "reference" and item.get("reference_request_id") == request_id:
            item["ready"] = True
            changed = True
    if changed:
        application.docs_checklist = items
        # Same JSON-column pitfall as update_docs_item: the dicts in `items`
        # were mutated in place, so SQLAlchemy sees no value change at flush
        # and silently drops the UPDATE without flag_modified.
        flag_modified(application, "docs_checklist")
    return changed


def link_checklist_item(application: Application, item_id: str, request_id: int) -> None:
    items = list(application.docs_checklist or [])
    for item in items:
        if item.get("id") == item_id:
            item["reference_request_id"] = request_id
    application.docs_checklist = items
    flag_modified(application, "docs_checklist")


def mark_sent(db: Session, request: ReferenceRequest) -> None:
    request.status = "sent"
    request.sent_at = utcnow()
    db.commit()


def mark_received(db: Session, request: ReferenceRequest, application: Application) -> None:
    request.status = "received"
    _flip_checklist_item(application, request.id)
    db.commit()


def check_overdue_and_due_soon(db: Session, user_id: int) -> list[ReferenceRequest]:
    """Flips any past-due "sent" request to "overdue"; returns everything
    that should surface as an urgent dashboard item (overdue, or sent with
    follow_up_at in the past)."""

    now = utcnow()
    surfaced: list[ReferenceRequest] = []
    changed = False
    for req in request_repo.list_by_user(db, user_id):
        if req.status == "sent" and req.due_at and req.due_at < now:
            req.status = "overdue"
            changed = True
        if req.status in ("overdue",) or (req.status == "sent" and req.follow_up_at and req.follow_up_at <= now):
            surfaced.append(req)
    # Called from GET /dashboard — only write when a status actually flipped
    # so the common read path stays read-only.
    if changed:
        db.commit()
    return surfaced
