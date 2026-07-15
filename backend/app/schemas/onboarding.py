from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PublicationOut(BaseModel):
    title: Optional[str] = None
    venue: Optional[str] = None
    year: Optional[int] = None


class ExtractedProfileOut(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    research_summary: Optional[str] = None
    research_areas: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    degree_subject: Optional[str] = None
    graduation_year: Optional[int] = None
    career_stage: Optional[str] = None
    languages_spoken: list[str] = Field(default_factory=list)
    publications: list[dict[str, Any]] = Field(default_factory=list)
    geographic_hints: list[str] = Field(default_factory=list)


class OnboardingProfileRequest(BaseModel):
    full_name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    research_summary: Optional[str] = None
    interests: Optional[str] = None
    skills: Optional[list[Any]] = None
    education: Optional[list[Any]] = None
    publications: Optional[list[Any]] = None
    languages: Optional[str] = None
    location_prefs: Optional[str] = None


class OnboardingConstraintsRequest(BaseModel):
    funding_required: Optional[Literal["yes", "no", "preferred"]] = None
    countries: Optional[list[str]] = None
    start_date_window: Optional[Literal["0-3m", "3-6m", "6-12m", "flexible"]] = None
    application_type: Optional[Literal["phd", "postdoc", "both"]] = None
    hard_constraints_text: Optional[str] = None


class OnboardingCompleteResponse(BaseModel):
    ok: bool = True


class OkResponse(BaseModel):
    ok: bool = True
