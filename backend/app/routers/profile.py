from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.services.cv_intake import store_and_extract_cv
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

    filename, text, sha = await store_and_extract_cv(file, current_user.id, db)
    return CVUploadResult(filename=filename, text_length=len(text), sha256=sha)
