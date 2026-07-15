from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.services import mailer
from shared.config import get_settings
from shared.database import get_db
from shared.llm import get_llm
from shared.models import Contact, Outreach, User
from shared.models.base import utcnow
from shared.repositories import jobs as jobs_repo
from shared.repositories import users as users_repo
from app.schemas.deepdive import (
    ContactRead,
    DeepDiveRequest,
    OutreachChatRequest,
    OutreachChatResponse,
    OutreachRead,
    OutreachUpdate,
    OutreachWithContact,
    SaveEmailRequest,
)
from app.schemas.job import RunResponse

router = APIRouter(prefix="/api", tags=["deepdive"])


def _get_outreach_with_contact(db: Session, outreach_id: int, user_id: int) -> tuple[Outreach, Contact]:
    outreach = db.scalar(select(Outreach).where(Outreach.id == outreach_id, Outreach.user_id == user_id))
    if outreach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outreach not found")
    contact = db.get(Contact, outreach.contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outreach contact not found")
    return outreach, contact


@router.post("/deepdive", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_deepdive(
    body: DeepDiveRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    if not body.professor_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="professor_name required")

    job = jobs_repo.create(db, current_user.id, job_type="deep_dive")
    from worker.tasks.deep_dive import deep_dive

    background_tasks.add_task(
        deep_dive,
        current_user.id,
        job.id,
        professor_name=body.professor_name,
        institution=body.institution,
        lab_url=body.lab_url,
        topic=body.topic,
        personal_note=body.personal_note,
    )
    # Note: the deep_dive task signature uses kwargs; FastAPI's BackgroundTasks
    # supports them when the underlying function does.
    return RunResponse(job_id=job.id)


@router.get("/deepdive/{outreach_id}", response_model=OutreachWithContact)
def get_deepdive(
    outreach_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachWithContact:
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)
    return OutreachWithContact(
        outreach=OutreachRead.model_validate(outreach),
        contact=ContactRead.model_validate(contact),
    )


@router.get("/outreach", response_model=list[OutreachWithContact])
def list_outreach(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OutreachWithContact]:
    outreaches = list(
        db.scalars(
            select(Outreach)
            .where(Outreach.user_id == current_user.id)
            .order_by(Outreach.created_at.desc())
        )
    )
    # One IN query instead of a db.get per row (N+1), and dangling
    # contact_ids skip the row instead of 500ing on model_validate(None).
    contacts = {
        c.id: c
        for c in db.scalars(select(Contact).where(Contact.id.in_({o.contact_id for o in outreaches})))
    } if outreaches else {}
    results: list[OutreachWithContact] = []
    for outreach in outreaches:
        contact = contacts.get(outreach.contact_id)
        if contact is None:
            continue
        results.append(
            OutreachWithContact(
                outreach=OutreachRead.model_validate(outreach),
                contact=ContactRead.model_validate(contact),
            )
        )
    return results


@router.patch("/outreach/{outreach_id}", response_model=OutreachWithContact)
def update_outreach(
    outreach_id: int,
    body: OutreachUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachWithContact:
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)

    if body.draft_email is not None:
        outreach.draft_email = body.draft_email
    if body.status is not None:
        outreach.status = body.status
    # Section 16 / 12: only store manually-confirmed emails. The PATCH path is
    # how the user supplies one.
    if body.email is not None:
        contact.email = body.email
    db.commit()
    db.refresh(outreach)
    db.refresh(contact)
    return OutreachWithContact(
        outreach=OutreachRead.model_validate(outreach),
        contact=ContactRead.model_validate(contact),
    )


@router.delete("/outreach/{outreach_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outreach(
    outreach_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Removes a supervisor research thread — the deep-dive task always
    creates exactly one Contact per Outreach, so both go together."""
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)
    db.delete(outreach)
    db.delete(contact)
    db.commit()


@router.post("/outreach/{outreach_id}/send", response_model=OutreachWithContact)
def send_outreach(
    outreach_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachWithContact:
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)
    if not contact.email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="add and confirm the professor's email address before sending",
        )
    if not outreach.email_subject or not outreach.email_body:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="outreach has no drafted email yet")

    profile = users_repo.get_profile(db, current_user.id)
    sender_name = current_user.full_name or (profile.full_name if profile else None)
    reply_to = (profile.contact_email if profile else None) or current_user.email

    try:
        mailer.send(
            to=contact.email,
            subject=outreach.email_subject,
            body=outreach.email_body,
            sender_name=sender_name,
            reply_to=reply_to,
        )
    except mailer.MailerNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except mailer.MailerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    outreach.status = "SENT"
    outreach.sent_at = utcnow()
    db.commit()
    db.refresh(outreach)
    return OutreachWithContact(outreach=OutreachRead.model_validate(outreach), contact=ContactRead.model_validate(contact))


@router.post("/outreach/{outreach_id}/copy", response_model=OutreachWithContact)
def copy_outreach(
    outreach_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachWithContact:
    """The user copied the drafted email themselves — mark it sent on trust,
    same convention as reference-request copy."""
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)
    outreach.status = "SENT"
    outreach.sent_at = utcnow()
    db.commit()
    db.refresh(outreach)
    return OutreachWithContact(outreach=OutreachRead.model_validate(outreach), contact=ContactRead.model_validate(contact))


@router.post("/outreach/{outreach_id}/chat", response_model=OutreachChatResponse)
def chat_outreach(
    outreach_id: int,
    body: OutreachChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachChatResponse:
    """Ask the AI to revise the drafted outreach email — same "ask the AI to
    change it" pattern as document chat-refinement, applied to subject+body."""
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)
    profile = users_repo.get_profile(db, current_user.id)

    settings = get_settings()
    llm = get_llm(settings.llm, role="refiner")
    history = list(outreach.chat_history or [])
    refined = llm.refine_email(
        "supervisor_outreach",
        outreach.email_subject or "",
        outreach.email_body or "",
        [{"role": h.get("role", "user"), "content": h.get("content", "")} for h in history],
        body.message,
        context={
            "professor_name": contact.professor_name,
            "institution": contact.institution,
            "research_summary": contact.research_summary,
            "publications": contact.publications,
            "student": {
                "full_name": profile.full_name if profile else None,
                "research_summary": profile.research_summary if profile else None,
            },
        },
    )

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": refined.assistant_reply})

    outreach.email_subject = refined.subject
    outreach.email_body = refined.body
    outreach.draft_email = f"Subject: {refined.subject}\n\n{refined.body}"
    outreach.chat_history = history
    db.commit()
    db.refresh(outreach)
    return OutreachChatResponse(
        outreach=OutreachRead.model_validate(outreach),
        contact=ContactRead.model_validate(contact),
        assistant_reply=refined.assistant_reply,
    )


@router.post("/outreach/{outreach_id}/save-email", response_model=OutreachWithContact)
def save_email(
    outreach_id: int,
    body: SaveEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutreachWithContact:
    outreach, contact = _get_outreach_with_contact(db, outreach_id, current_user.id)

    outreach.email_subject = body.subject
    outreach.email_body = body.body
    outreach.draft_email = f"Subject: {body.subject}\n\n{body.body}"
    db.commit()
    db.refresh(outreach)
    return OutreachWithContact(
        outreach=OutreachRead.model_validate(outreach),
        contact=ContactRead.model_validate(contact),
    )
