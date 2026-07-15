from typing import Literal, Optional

from pydantic import BaseModel


class UrgencyCta(BaseModel):
    label: str
    href: str


class UrgencyItem(BaseModel):
    kind: Literal["deadline_near", "letter_ready_to_send", "reference_overdue", "reference_due_soon"]
    application_id: int
    title: str
    institution: Optional[str] = None
    days_until: int
    cta: UrgencyCta


class RecentSearchItem(BaseModel):
    id: int
    url: str
    status: str
    listings_matched: int
    created_at: str


class LastRun(BaseModel):
    search_run_id: Optional[int] = None
    finished_at: Optional[str] = None
    listings_matched: Optional[int] = None
    summary: str


class DashboardStats(BaseModel):
    opportunities: int
    avg_match: Optional[float] = None
    applications: int
    interviews: int
    offers: int
    upcoming_deadlines: int
    excellent_matches: int


class PipelineStage(BaseModel):
    key: str
    label: str
    count: int


class FeaturedOpportunity(BaseModel):
    listing_id: int
    application_id: Optional[int] = None
    title: str
    institution: Optional[str] = None
    score: float
    funding_type: str
    deadline: Optional[str] = None
    days_until_deadline: Optional[int] = None


class NextAction(BaseModel):
    label: str
    href: str
    kind: Literal["deadline", "docs", "reference", "cv", "generic"] = "generic"


class DashboardResponse(BaseModel):
    urgent: list[UrgencyItem]
    recent_searches: list[RecentSearchItem]
    last_run: LastRun
    stats: DashboardStats
    pipeline: list[PipelineStage]
    featured: Optional[FeaturedOpportunity] = None
    next_actions: list[NextAction]
