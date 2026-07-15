from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    score: float
    fit_breakdown: Optional[dict[str, Any]] = None
    reasons: Optional[str] = None
    red_flags: Optional[list[Any]] = None
    model_used: Optional[str] = None
    fit_paragraph: Optional[str] = None
    scored_at: datetime


class FitExplanation(BaseModel):
    paragraph: str


class ListingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: Optional[str] = None
    institution: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    research_field: Optional[str] = None
    offer_type: Optional[str] = None
    deadline: Optional[datetime] = None
    parsed_ok: bool


class ListingWithScore(ListingSummary):
    latest_score: Optional[ScoreRead] = None


class ListingDetail(ListingWithScore):
    source: str
    source_key: str
    url: Optional[str] = None
    funding_info: Optional[str] = None
    contact_email: Optional[str] = None
    application_url: Optional[str] = None
    required_docs: Optional[list[Any]] = None
    description: Optional[str] = None
    supervisor_name: Optional[str] = None  # never extracted today; always null
    first_seen: datetime
    last_seen: datetime


class ListingRow(ListingWithScore):
    """Row shape for the /opportunities table (Phase 06) — adds the
    Application join + a keyword-derived funding classification."""

    supervisor_name: Optional[str] = None  # never extracted today; always null
    funding_type: str = "unknown"  # "fully_funded" | "partial" | "unknown"
    status: Optional[str] = None  # Application.status, if tracked
    application_id: Optional[int] = None
