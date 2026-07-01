from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.config import get_settings as get_app_settings
from shared.database import get_db
from shared.models import User
from shared.repositories import users as users_repo
from app.schemas.profile import (
    CVUploadResult,
    ProfileRead,
    ProfileUpdate,
    SettingsRead,
    SettingsUpdate,
)
from shared.cv.extract import SUPPORTED, cv_sha256, extract_cv_text

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=ProfileRead)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    return ProfileRead.model_validate(profile)


@router.put("/profile", response_model=ProfileRead)
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileRead:
    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field_name, value)
    db.commit()
    db.refresh(profile)
    return ProfileRead.model_validate(profile)


@router.get("/settings", response_model=SettingsRead)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsRead:
    settings = users_repo.get_settings(db, current_user.id)
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="settings not found")
    return SettingsRead.model_validate(settings)


@router.put("/settings", response_model=SettingsRead)
def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsRead:
    settings = users_repo.get_settings(db, current_user.id)
    if settings is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="settings not found")
    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field_name, value)
    db.commit()
    db.refresh(settings)
    return SettingsRead.model_validate(settings)


@router.post("/profile/cv", response_model=CVUploadResult)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CVUploadResult:
    """Upload a CV (PDF, DOCX, TXT, or MD). The file is stored, text is
    extracted with pypdf/python-docx, and saved to Profile.cv_text so the
    scorer and drafter can use it directly."""

    filename = file.filename or "cv.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type {suffix!r}. Supported: {', '.join(SUPPORTED)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    sha = cv_sha256(content)
    app_settings = get_app_settings()
    cv_dir = app_settings.storage_dir / "cvs" / f"user_{current_user.id}"
    cv_dir.mkdir(parents=True, exist_ok=True)
    save_path = cv_dir / f"{sha[:16]}{suffix}"
    save_path.write_bytes(content)

    try:
        text = extract_cv_text(save_path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    profile.cv_filename = filename
    profile.cv_path = str(save_path)
    profile.cv_text = text
    profile.cv_sha256 = sha
    db.commit()

    return CVUploadResult(filename=filename, text_length=len(text), sha256=sha)
