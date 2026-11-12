from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.document import (
    DocType,
    DocumentChatRequest,
    DocumentChatResponse,
    DocumentEditRequest,
    DocumentVersionRead,
)
from app.services import documents as doc_service
from shared.database import get_db
from app.routers._shared import get_application_or_404
from shared.repositories import users as users_repo
from shared.models import User

router = APIRouter(prefix="/api/applications/{application_id}/documents", tags=["documents"])



@router.post("/{doc_type}", response_model=DocumentVersionRead)
def generate_document(
    application_id: int,
    doc_type: DocType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionRead:
    app = get_application_or_404(db, current_user, application_id)
    profile = users_repo.get_profile(db, current_user.id)
    version = doc_service.generate(db, app, profile, doc_type)
    db.commit()
    return DocumentVersionRead.model_validate(version)


@router.post("/{doc_type}/chat", response_model=DocumentChatResponse)
def chat_document(
    application_id: int,
    doc_type: DocType,
    body: DocumentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChatResponse:
    app = get_application_or_404(db, current_user, application_id)
    profile = users_repo.get_profile(db, current_user.id)
    version, reply = doc_service.refine(db, app, profile, doc_type, body.message)
    db.commit()
    return DocumentChatResponse(version=DocumentVersionRead.model_validate(version), assistant_reply=reply)


@router.patch("/{doc_type}", response_model=DocumentVersionRead)
def edit_document(
    application_id: int,
    doc_type: DocType,
    body: DocumentEditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionRead:
    """The user writing their own change directly, as a new version."""
    app = get_application_or_404(db, current_user, application_id)
    version = doc_service.save_edit(db, app, doc_type, body.body_markdown)
    db.commit()
    return DocumentVersionRead.model_validate(version)


@router.get("/{doc_type}", response_model=DocumentVersionRead)
def get_document(
    application_id: int,
    doc_type: DocType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionRead:
    app = get_application_or_404(db, current_user, application_id)
    version = doc_service.get_current(db, app, doc_type)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no draft yet — POST to generate one")
    return DocumentVersionRead.model_validate(version)


@router.get("/{doc_type}/versions", response_model=list[DocumentVersionRead])
def list_versions(
    application_id: int,
    doc_type: DocType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentVersionRead]:
    app = get_application_or_404(db, current_user, application_id)
    versions = doc_service.list_versions(db, app, doc_type)
    return [DocumentVersionRead.model_validate(v) for v in versions]


@router.post("/{doc_type}/versions/{version_number}/revert", response_model=DocumentVersionRead)
def revert_document(
    application_id: int,
    doc_type: DocType,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentVersionRead:
    app = get_application_or_404(db, current_user, application_id)
    try:
        version = doc_service.revert(db, app, doc_type, version_number)
    except doc_service.VersionNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
    db.commit()
    return DocumentVersionRead.model_validate(version)


@router.get("/{doc_type}/download.pdf")
def download_pdf(
    application_id: int,
    doc_type: DocType,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    app = get_application_or_404(db, current_user, application_id)
    version = doc_service.get_current(db, app, doc_type)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no draft yet")
    profile = users_repo.get_profile(db, current_user.id)
    try:
        pdf_bytes = doc_service.render_pdf(version, profile)
    except doc_service.PdfUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc_type}.pdf"'},
    )
