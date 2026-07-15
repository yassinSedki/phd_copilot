import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.onboarding import (
    ExtractedProfileOut,
    OkResponse,
    OnboardingCompleteResponse,
    OnboardingConstraintsRequest,
    OnboardingProfileRequest,
)
from app.services.cv_intake import store_and_extract_cv
from shared.config import get_settings as get_app_settings
from shared.database import get_db
from shared.llm import get_llm
from shared.models import User
from shared.repositories import users as users_repo

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


def _profile_step_done(profile) -> bool:
    return bool(profile and (profile.full_name or profile.research_summary))


@router.post("/cv", response_model=ExtractedProfileOut)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractedProfileOut:
    _, text, _ = await store_and_extract_cv(file, current_user.id, db)

    # The LLM extraction is a blocking network call — keep it off the loop.
    llm = get_llm(get_app_settings().llm, role="builder")
    extracted = await asyncio.to_thread(llm.extract_profile_from_cv, text)

    return ExtractedProfileOut(
        full_name=extracted.full_name,
        email=extracted.email,
        phone=extracted.phone,
        research_summary=extracted.research_summary,
        research_areas=extracted.research_areas,
        methods=extracted.methods,
        programming_languages=extracted.programming_languages,
        degree_subject=extracted.degree_subject,
        graduation_year=extracted.graduation_year,
        career_stage=extracted.career_stage,
        languages_spoken=extracted.languages_spoken,
        publications=extracted.publications,
        geographic_hints=extracted.geographic_hints,
    )


@router.post("/profile", response_model=OkResponse)
def save_profile(
    body: OnboardingProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OkResponse:
    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    for field_name, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field_name, value)
    db.commit()
    return OkResponse()


@router.post("/constraints", response_model=OkResponse)
def save_constraints(
    body: OnboardingConstraintsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OkResponse:
    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    if not _profile_step_done(profile):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="complete the profile step (POST /onboarding/profile) before constraints",
        )
    profile.profile_constraints = body.model_dump(exclude_unset=True)
    db.commit()
    return OkResponse()


@router.post("/complete", response_model=OnboardingCompleteResponse)
def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingCompleteResponse:
    profile = users_repo.get_profile(db, current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="profile not found")
    if not _profile_step_done(profile):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="profile step not completed")
    if profile.profile_constraints is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="constraints step not completed")
    profile.is_onboarded = True
    db.commit()
    return OnboardingCompleteResponse(ok=True)
