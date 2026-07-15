from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.reference_request import (
    ReferencePreviewRequest,
    ReferencePreviewResponse,
    ReferenceRequestChatRequest,
    ReferenceRequestChatResponse,
    ReferenceRequestCreate,
    ReferenceRequestEdit,
    ReferenceRequestRead,
    ReferenceRequestWithReferee,
)
from app.schemas.referee import RefereeRead
from app.services import mailer
from app.services import reference_requests as ref_service
from shared.database import get_db
from shared.models import User
from shared.repositories import applications as app_repo
from app.routers._shared import get_application_or_404
from shared.repositories import referees as referee_repo
from shared.repositories import reference_requests as request_repo
from shared.repositories import users as users_repo

router = APIRouter(prefix="/api/reference-requests", tags=["reference-requests"])



def _to_with_referee(db: Session, request) -> ReferenceRequestWithReferee:
    referee = referee_repo.get(db, request.referee_id, request.user_id)
    return ReferenceRequestWithReferee(
        request=ReferenceRequestRead.model_validate(request),
        referee=RefereeRead.model_validate(referee),
    )


@router.post("/preview", response_model=ReferencePreviewResponse)
def preview(
    body: ReferencePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferencePreviewResponse:
    """Pure LLM call — no DB write. If `referee_id` is given it's a
    read-only lookup; otherwise the payload is built straight from the
    request fields (the referee row is only created on actual submit)."""

    app = get_application_or_404(db, current_user, body.application_id)

    if body.referee_id is not None:
        referee = referee_repo.get(db, body.referee_id, current_user.id)
        if referee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referee not found")
        payload = ref_service.referee_payload(referee)
    else:
        if not body.referee_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="referee_id or referee_name required")
        payload = ref_service.referee_payload_from_fields(body.referee_name, body.referee_title)

    profile = users_repo.get_profile(db, current_user.id)
    subject, draft_body = ref_service.draft_preview(db, app, profile, payload, body.submission_method, body.personal_note)
    return ReferencePreviewResponse(subject=subject, body=draft_body)


@router.get("", response_model=list[ReferenceRequestWithReferee])
def list_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReferenceRequestWithReferee]:
    return [_to_with_referee(db, r) for r in request_repo.list_by_user(db, current_user.id)]


@router.get("/{request_id}", response_model=ReferenceRequestWithReferee)
def get_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    return _to_with_referee(db, req)


@router.post("", response_model=ReferenceRequestWithReferee, status_code=status.HTTP_201_CREATED)
def create_request(
    body: ReferenceRequestCreate,
    item_id: str | None = Query(None, description="Checklist item id to link this request to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    app = get_application_or_404(db, current_user, body.application_id)
    try:
        referee = ref_service.get_or_create_referee(
            db,
            current_user.id,
            referee_id=body.referee_id,
            name=body.referee_name,
            title=body.referee_title,
            email=body.referee_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    profile = users_repo.get_profile(db, current_user.id)
    subject, draft_body = ref_service.draft_preview(
        db, app, profile, ref_service.referee_payload(referee), body.submission_method, body.personal_note
    )
    request = ref_service.create_request(
        db,
        current_user.id,
        referee=referee,
        application=app,
        submission_method=body.submission_method,
        subject=subject,
        body=draft_body,
    )
    if item_id:
        ref_service.link_checklist_item(app, item_id, request.id)
        db.commit()
    return _to_with_referee(db, request)


@router.patch("/{request_id}", response_model=ReferenceRequestWithReferee)
def edit_request(
    request_id: int,
    body: ReferenceRequestEdit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    """The user writing their own change to the subject/body directly."""
    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    ref_service.update_draft(db, req, subject=body.subject, body=body.body)
    return _to_with_referee(db, req)


@router.post("/{request_id}/chat", response_model=ReferenceRequestChatResponse)
def chat_request(
    request_id: int,
    body: ReferenceRequestChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestChatResponse:
    """Ask the AI to revise the drafted email — same "ask the AI to change
    it" pattern as document chat-refinement, applied to subject+body."""
    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    referee = referee_repo.get(db, req.referee_id, current_user.id)
    if referee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referee not found")
    app = get_application_or_404(db, current_user, req.application_id)
    profile = users_repo.get_profile(db, current_user.id)

    reply = ref_service.refine_draft(db, req, referee, app, profile, body.message)
    return ReferenceRequestChatResponse(
        request=ReferenceRequestRead.model_validate(req),
        referee=RefereeRead.model_validate(referee),
        assistant_reply=reply,
    )


@router.post("/{request_id}/send", response_model=ReferenceRequestWithReferee)
def send_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    referee = referee_repo.get(db, req.referee_id, current_user.id)
    if referee is None or not req.email_subject or not req.email_body:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="request has no drafted email yet")

    profile = users_repo.get_profile(db, current_user.id)
    sender_name = current_user.full_name or (profile.full_name if profile else None)
    reply_to = (profile.contact_email if profile else None) or current_user.email

    try:
        mailer.send(
            to=referee.email,
            subject=req.email_subject,
            body=req.email_body,
            sender_name=sender_name,
            reply_to=reply_to,
        )
    except mailer.MailerNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except mailer.MailerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    ref_service.mark_sent(db, req)
    return _to_with_referee(db, req)


@router.post("/{request_id}/copy", response_model=ReferenceRequestWithReferee)
def copy_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    """The user copied the drafted email themselves — mark it sent on trust."""

    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    ref_service.mark_sent(db, req)
    return _to_with_referee(db, req)


@router.post("/{request_id}/mark-received", response_model=ReferenceRequestWithReferee)
def mark_received(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceRequestWithReferee:
    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    app = get_application_or_404(db, current_user, req.application_id)
    ref_service.mark_received(db, req, app)
    return _to_with_referee(db, req)


@router.post("/{request_id}/follow-up", response_model=ReferencePreviewResponse)
def follow_up(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferencePreviewResponse:
    """Drafts a follow-up (does not send — the modal offers send/copy same
    as the original request)."""

    req = request_repo.get(db, request_id, current_user.id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reference request not found")
    referee = referee_repo.get(db, req.referee_id, current_user.id)
    app = get_application_or_404(db, current_user, req.application_id)
    if referee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="referee not found")

    from shared.config import get_settings
    from shared.llm import get_llm

    settings = get_settings()
    llm = get_llm(settings.llm, role="drafter")
    draft = llm.draft_reference_followup(
        {"name": referee.name, "title": referee.title, "institution": referee.institution},
        {"title": app.listing.title, "institution": app.listing.institution},
        req.sent_at.isoformat() if req.sent_at else None,
        req.due_at.isoformat() if req.due_at else None,
    )
    return ReferencePreviewResponse(subject=draft.subject, body=draft.body)
