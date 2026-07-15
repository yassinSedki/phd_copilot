from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import CoverLetter, ReferenceRequest, User
from shared.repositories import applications as app_repo
from shared.repositories import users as users_repo
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationRead,
    ApplicationRow,
    ApplicationUpdate,
    BulkActionRequest,
    BulkActionResponse,
    BulkResultItem,
    DocsChecklistItemUpdate,
    DocsChecklistUpdate,
    ReferenceCounts,
)
from app.schemas.letter import (
    CoverLetterChatRequest,
    CoverLetterChatResponse,
    CoverLetterRead,
)
from shared.services import applications as app_service
from app.services import cover_letters as cl_service
from shared.services import state_machine as sm

router = APIRouter(prefix="/api/applications", tags=["applications"])

ACTIVE_STATUSES = {sm.SAVED, sm.IN_PROGRESS, sm.DOCS_READY, sm.APPLIED, sm.INTERVIEW}
CLOSED_STATUSES = {sm.OFFER, sm.REJECTED, sm.WITHDRAWN}


def _cover_letter_status(cover) -> Optional[str]:
    if cover is None or not cover.body_markdown:
        return None
    if cover.email_subject and cover.email_body:
        return "done"
    if cover.chat_history and len(cover.chat_history) > 1:
        return "refined"
    return "draft"


def _readiness_score(docs_checklist) -> int:
    items = docs_checklist or []
    if not items:
        return 0
    done = sum(1 for item in items if item.get("ready"))
    return round(done / len(items) * 100)


def _reference_counts(application, requested_count: int) -> ReferenceCounts:
    required_count = sum(1 for item in (application.docs_checklist or []) if item.get("kind") == "reference")
    return ReferenceCounts(requested=requested_count, required=max(required_count, requested_count))


def _to_row(application, cover, requested_refs: int) -> ApplicationRow:
    notes = application.notes or None
    return ApplicationRow(
        id=application.id,
        title=application.listing.title,
        institution=application.listing.institution,
        supervisor_name=None,  # never extracted today — see Phase 06/07 notes
        deadline=application.deadline,
        status=application.status,
        priority=application.priority,
        cover_letter_status=_cover_letter_status(cover),
        sop_status=None,
        references=_reference_counts(application, requested_refs),
        readiness_score=_readiness_score(application.docs_checklist),
        notes_preview=notes[:80] if notes else None,
    )


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    sort: str = Query("deadline", pattern="^(deadline|readiness|status|title)$"),
    dir: str = Query("asc", pattern="^(asc|desc)$"),
    status_filter: str = Query("active", alias="status", pattern="^(active|closed|all)$"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationListResponse:
    apps = app_repo.list_for_user(db, current_user.id)

    if status_filter == "active":
        apps = [a for a in apps if a.status in ACTIVE_STATUSES]
    elif status_filter == "closed":
        apps = [a for a in apps if a.status in CLOSED_STATUSES]

    # Batch the per-row lookups (cover letter + reference counts) into two
    # IN/grouped queries — the old per-application queries were O(rows).
    ids = [a.id for a in apps]
    covers = (
        {c.application_id: c for c in db.scalars(select(CoverLetter).where(CoverLetter.application_id.in_(ids)))}
        if ids
        else {}
    )
    ref_counts = (
        dict(
            db.execute(
                select(ReferenceRequest.application_id, func.count())
                .where(ReferenceRequest.application_id.in_(ids))
                .group_by(ReferenceRequest.application_id)
            ).all()
        )
        if ids
        else {}
    )
    rows = [_to_row(a, covers.get(a.id), ref_counts.get(a.id, 0)) for a in apps]

    reverse = dir == "desc"
    if sort == "deadline":
        rows.sort(key=lambda r: (r.deadline is None, r.deadline), reverse=reverse)
    elif sort == "readiness":
        rows.sort(key=lambda r: r.readiness_score, reverse=reverse)
    elif sort == "status":
        rows.sort(key=lambda r: r.status, reverse=reverse)
    elif sort == "title":
        rows.sort(key=lambda r: (r.title or ""), reverse=reverse)

    return ApplicationListResponse(items=rows[:limit], total=len(rows))


@router.post("/bulk", response_model=BulkActionResponse)
def bulk_action(
    body: BulkActionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkActionResponse:
    target_status = sm.WITHDRAWN if body.action == "archive" else body.status
    results: list[BulkResultItem] = []
    # One transaction for the whole batch: per-item commits meant a failure
    # mid-loop left earlier items already persisted.
    for app_id in body.ids:
        app = app_repo.get(db, current_user.id, app_id)
        if app is None:
            results.append(BulkResultItem(id=app_id, ok=False, error="not found"))
            continue
        try:
            app_service.update_application(db, application=app, status=target_status, commit=False)
            results.append(BulkResultItem(id=app_id, ok=True))
        except (sm.IllegalTransition, sm.GuardFailed) as exc:
            results.append(BulkResultItem(id=app_id, ok=False, error=str(exc)))
    db.commit()
    return BulkActionResponse(results=results)


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    try:
        app = app_service.create_application(
            db,
            user_id=current_user.id,
            listing_id=body.listing_id,
            priority=body.priority,
            notes=body.notes,
        )
    except app_service.ListingNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing not found")
    except app_service.AlreadyTracked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application already exists for this listing")
    db.refresh(app, attribute_names=["listing"])
    return ApplicationRead.model_validate(app)


@router.get("/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    return ApplicationRead.model_validate(app)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not app_repo.delete(db, current_user.id, application_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")


@router.patch("/{application_id}", response_model=ApplicationRead)
def patch_application(
    application_id: int,
    body: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    try:
        app = app_service.update_application(
            db,
            application=app,
            status=body.status,
            priority=body.priority,
            deadline=body.deadline,
            notes=body.notes,
            next_action=body.next_action,
            next_action_date=body.next_action_date,
        )
    except sm.IllegalTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except sm.GuardFailed as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ApplicationRead.model_validate(app)


@router.patch("/{application_id}/docs", response_model=ApplicationRead)
def patch_docs(
    application_id: int,
    body: DocsChecklistUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    items = [item.model_dump() for item in body.items]
    app = app_service.update_docs(db, application=app, items=items)
    return ApplicationRead.model_validate(app)


@router.patch("/{application_id}/docs/{item_id}", response_model=ApplicationRead)
def patch_docs_item(
    application_id: int,
    item_id: str,
    body: DocsChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    """Atomic per-item update — avoids write races when several checklist
    checkboxes are toggled in quick succession (Phase 09)."""

    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    try:
        app = app_service.update_docs_item(
            db, application=app, item_id=item_id, fields=body.model_dump(exclude_unset=True)
        )
    except app_service.ChecklistItemNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="checklist item not found")
    return ApplicationRead.model_validate(app)


@router.post("/{application_id}/checklist/regenerate", response_model=ApplicationRead)
def regenerate_checklist(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    app = app_service.regenerate_checklist(db, application=app, listing=app.listing)
    return ApplicationRead.model_validate(app)


# ----- Cover letter (conversational; phd copilot.md "Conversational cover letter editor")


@router.post("/{application_id}/cover-letter", response_model=CoverLetterRead)
def generate_letter(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverLetterRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    profile = users_repo.get_profile(db, current_user.id)
    cover = cl_service.generate_initial(db, app, profile)
    db.commit()
    db.refresh(cover)
    return CoverLetterRead.model_validate(cover)


@router.post("/{application_id}/cover-letter/chat", response_model=CoverLetterChatResponse)
def chat_letter(
    application_id: int,
    body: CoverLetterChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverLetterChatResponse:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    profile = users_repo.get_profile(db, current_user.id)
    cover, reply = cl_service.refine_via_chat(db, app, profile, body.message)
    db.commit()
    db.refresh(cover)
    return CoverLetterChatResponse(letter=CoverLetterRead.model_validate(cover), assistant_reply=reply)


@router.get("/{application_id}/cover-letter", response_model=CoverLetterRead)
def get_letter(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverLetterRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    cover = cl_service.get_letter(db, app)
    if cover is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no letter yet — POST to generate one")
    return CoverLetterRead.model_validate(cover)


@router.get("/{application_id}/cover-letter/download", response_class=PlainTextResponse)
def download_letter(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    cover = cl_service.get_letter(db, app)
    if cover is None or not cover.body_markdown:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="letter not generated yet")
    return PlainTextResponse(
        cover.body_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cover_letter_{application_id}.md"'},
    )


# ----- Outreach email body (phd copilot.md "Outreach email drafting")


@router.post("/{application_id}/email-draft", response_model=CoverLetterRead)
def email_draft(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverLetterRead:
    app = app_repo.get(db, current_user.id, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    profile = users_repo.get_profile(db, current_user.id)
    cl_service.draft_email(db, app, profile)
    db.commit()
    cover = cl_service.get_letter(db, app)
    return CoverLetterRead.model_validate(cover)
