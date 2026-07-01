from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import Contact, Outreach, User
from shared.repositories import jobs as jobs_repo
from app.schemas.deepdive import (
    ContactRead,
    DeepDiveRequest,
    OutreachRead,
    OutreachUpdate,
    OutreachWithContact,
)
from app.schemas.job import RunResponse

router = APIRouter(prefix="/api", tags=["deepdive"])


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
    outreach = db.scalar(
        select(Outreach).where(Outreach.id == outreach_id, Outreach.user_id == current_user.id)
    )
    if outreach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outreach not found")
    contact = db.get(Contact, outreach.contact_id)
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
    results: list[OutreachWithContact] = []
    for outreach in outreaches:
        contact = db.get(Contact, outreach.contact_id)
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
    outreach = db.scalar(
        select(Outreach).where(Outreach.id == outreach_id, Outreach.user_id == current_user.id)
    )
    if outreach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="outreach not found")

    if body.draft_email is not None:
        outreach.draft_email = body.draft_email
    if body.status is not None:
        outreach.status = body.status
    contact = db.get(Contact, outreach.contact_id)
    # Section 16 / 12: only store manually-confirmed emails. The PATCH path is
    # how the user supplies one.
    if body.email is not None and contact is not None:
        contact.email = body.email
    db.commit()
    db.refresh(outreach)
    if contact is not None:
        db.refresh(contact)
    return OutreachWithContact(
        outreach=OutreachRead.model_validate(outreach),
        contact=ContactRead.model_validate(contact),
    )
