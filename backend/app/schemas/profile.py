from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field  # noqa: F401


class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    # Contact details as extracted from the CV — distinct from the account's
    # login email, which is never overwritten by CV extraction.
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    research_summary: Optional[str] = None
    interests: Optional[str] = None
    skills: Optional[list[Any]] = None
    education: Optional[list[Any]] = None
    publications: Optional[list[Any]] = None
    languages: Optional[str] = None
    location_prefs: Optional[str] = None
    constraints: Optional[str] = None


class ProfileUpdate(ProfileBase):
    """Client-updatable fields only. `is_onboarded` is set exclusively by
    POST /onboarding/complete and `cv_path` by the CV upload flows — exposing
    them here let clients skip onboarding / overwrite the stored CV path."""


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    cv_path: Optional[str] = None
    cv_filename: Optional[str] = None
    cv_text: Optional[str] = None
    cv_sha256: Optional[str] = None
    # Structured search constraints (countries/funding/…) — editable from
    # Settings via POST /onboarding/constraints; drives the prefilter.
    profile_constraints: Optional[dict[str, Any]] = None
    is_onboarded: bool = False


class CVUploadResult(BaseModel):
    filename: str
    text_length: int
    sha256: str


class SettingsBase(BaseModel):
    filters: Optional[dict[str, Any]] = None
    score_threshold: int = Field(default=60, ge=0, le=100)
    scoring_model: Optional[str] = None
    drafting_model: Optional[str] = None
    schedule: Optional[str] = None


class SettingsUpdate(SettingsBase):
    pass


class SettingsRead(SettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
