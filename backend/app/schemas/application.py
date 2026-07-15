from datetime import datetime
from typing import Any, Literal, Optional, Union

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
    """One checklist entry. `kind` drives the frontend's action button —
    document | manual | reference | portal (Phase 09)."""

    id: str
    kind: Literal["document", "manual", "reference", "portal"] = "manual"
    label: str
    ready: bool = False
    doc_type: Optional[str] = None  # kind="document": cover_letter | sop | research_proposal
    url: Optional[str] = None  # kind="portal"
    referee_id: Optional[int] = None  # kind="reference"
    reference_request_id: Optional[int] = None  # kind="reference"


class DocsChecklistUpdate(BaseModel):
    items: list[DocsChecklistItem] = Field(default_factory=list)


class DocsChecklistItemUpdate(BaseModel):
    """Partial update for PATCH /applications/:id/docs/:item_id."""

    ready: Optional[bool] = None
    referee_id: Optional[int] = None
    reference_request_id: Optional[int] = None


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


class ReferenceCounts(BaseModel):
    requested: int
    required: int


class ApplicationRow(BaseModel):
    """Row shape for the /tracker table (Phase 08)."""

    id: int
    title: Optional[str] = None
    institution: Optional[str] = None
    supervisor_name: Optional[str] = None
    deadline: Optional[datetime] = None
    status: str
    priority: int
    cover_letter_status: Optional[str] = None  # draft | refined | done | null
    sop_status: Optional[str] = None  # never populated today — no SOP flow yet
    references: ReferenceCounts
    readiness_score: int
    notes_preview: Optional[str] = None


class ApplicationListResponse(BaseModel):
    items: list[ApplicationRow]
    total: int


class BulkSetStatusAction(BaseModel):
    ids: list[int]
    action: Literal["set_status"]
    status: str


class BulkArchiveAction(BaseModel):
    ids: list[int]
    action: Literal["archive"]


class BulkResultItem(BaseModel):
    id: int
    ok: bool
    error: Optional[str] = None


class BulkActionResponse(BaseModel):
    results: list[BulkResultItem]


BulkActionRequest = Union[BulkSetStatusAction, BulkArchiveAction]
