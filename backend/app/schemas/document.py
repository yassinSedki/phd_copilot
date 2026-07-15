from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

DocType = Literal["cover_letter", "sop", "research_proposal"]


class DocumentChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    at: Optional[datetime] = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    application_id: int
    doc_type: DocType
    version_number: int
    body_markdown: str
    created_by: Literal["user", "agent"]
    chat_history: list[DocumentChatTurn] = Field(default_factory=list)
    author_notes: Optional[str] = None
    warnings: list[Any] = Field(default_factory=list)
    created_at: datetime

    @field_validator("warnings", "chat_history", mode="before")
    @classmethod
    def _none_to_empty_list(cls, v: Any) -> Any:
        return [] if v is None else v


class DocumentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class DocumentChatResponse(BaseModel):
    version: DocumentVersionRead
    assistant_reply: str


class DocumentEditRequest(BaseModel):
    """The user writing their own change directly, as opposed to asking the
    AI via /chat. Saved as a new version, created_by="user"."""

    body_markdown: str = Field(min_length=1)
