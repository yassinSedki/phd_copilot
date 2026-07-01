from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.listing import ListingSummary


class ApplicationCreate(BaseModel):
    listing_id: int
    priority: int = 0
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[datetime] = None
    notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None


class DocsChecklistItem(BaseModel):
    doc: str
    ready: bool = False
    path: Optional[str] = None


class DocsChecklistUpdate(BaseModel):
    items: list[DocsChecklistItem] = Field(default_factory=list)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: int
    status: str
    priority: int
    deadline: Optional[datetime] = None
    docs_checklist: Optional[list[Any]] = None
    cover_letter_path: Optional[str] = None
    applied_at: Optional[datetime] = None
    next_action: Optional[str] = None
    next_action_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    listing: ListingSummary


class KanbanBoard(BaseModel):
    columns: dict[str, list[ApplicationRead]]
