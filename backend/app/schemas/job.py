from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    status: str
    progress: int
    progress_meta: Optional[dict[str, Any]] = None
    result_ref: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class RunResponse(BaseModel):
    job_id: int
    search_run_id: Optional[int] = None


class SearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    status: str
    pages_processed: int
    listings_found: int
    listings_matched: int
    job_id: Optional[int] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
