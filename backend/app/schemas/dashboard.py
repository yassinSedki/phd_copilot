from typing import Optional

from pydantic import BaseModel

from app.schemas.application import ApplicationRead
from app.schemas.listing import ListingWithScore


class StatusCounts(BaseModel):
    counts: dict[str, int]


class DashboardResponse(BaseModel):
    counts_by_status: dict[str, int]
    top_matches: list[ListingWithScore]
    upcoming_deadlines: list[ApplicationRead]
    action_needed: list[ApplicationRead]
    in_progress: list[ApplicationRead]
    total_listings: int
    total_applications: int
    last_run_at: Optional[str] = None
