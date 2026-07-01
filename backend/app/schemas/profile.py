from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field  # noqa: F401


class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    research_summary: Optional[str] = None
    interests: Optional[str] = None
    skills: Optional[list[Any]] = None
    education: Optional[list[Any]] = None
    publications: Optional[list[Any]] = None
    languages: Optional[str] = None
    location_prefs: Optional[str] = None
    constraints: Optional[str] = None
    cv_path: Optional[str] = None


class ProfileUpdate(ProfileBase):
    pass


class ProfileRead(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    cv_filename: Optional[str] = None
    cv_text: Optional[str] = None
    cv_sha256: Optional[str] = None


class CVUploadResult(BaseModel):
    filename: str
    text_length: int
    sha256: str


class SettingsBase(BaseModel):
    filters: Optional[dict[str, Any]] = None
    score_threshold: int = Field(default=70, ge=0, le=100)
    scoring_model: Optional[str] = None
    drafting_model: Optional[str] = None
    schedule: Optional[str] = None


class SettingsUpdate(SettingsBase):
    pass


class SettingsRead(SettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
