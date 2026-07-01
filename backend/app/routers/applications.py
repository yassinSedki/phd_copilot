from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import User
from shared.repositories import applications as app_repo
from shared.repositories import users as users_repo
from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    DocsChecklistUpdate,
    KanbanBoard,
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


@router.get("", response_model=KanbanBoard)
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KanbanBoard:
    apps = app_repo.list_for_user(db, current_user.id)
    columns: dict[str, list[ApplicationRead]] = {col: [] for col in sm.KANBAN_COLUMNS}
    for app in apps:
        bucket = columns.setdefault(app.status, [])
        bucket.append(ApplicationRead.model_validate(app))
    return KanbanBoard(columns=columns)


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
