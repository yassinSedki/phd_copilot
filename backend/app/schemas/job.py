from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    status: str
    progress: int
    result_ref: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class RunResponse(BaseModel):
    job_id: int
