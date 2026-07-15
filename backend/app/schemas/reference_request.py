from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.referee import RefereeRead

SubmissionMethod = Literal["portal", "forward_to_me", "other"]


class ChatTurn(BaseModel):
    role: str
    content: str


class ReferencePreviewRequest(BaseModel):
    referee_id: Optional[int] = None
    referee_name: Optional[str] = None
    referee_title: Optional[str] = None
    referee_email: Optional[EmailStr] = None
    application_id: int
    submission_method: SubmissionMethod = "portal"
    personal_note: Optional[str] = None


class ReferencePreviewResponse(BaseModel):
    subject: str
    body: str


class ReferenceRequestCreate(ReferencePreviewRequest):
    pass


class ReferenceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    referee_id: int
    application_id: int
    status: Literal["draft", "sent", "received", "overdue"]
    submission_method: SubmissionMethod
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    chat_history: list[ChatTurn] = Field(default_factory=list)
    sent_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    follow_up_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReferenceRequestWithReferee(BaseModel):
    request: ReferenceRequestRead
    referee: RefereeRead


class ReferenceRequestEdit(BaseModel):
    """Direct manual edit of the drafted email — the user writing their own
    change instead of asking the AI."""

    subject: Optional[str] = None
    body: Optional[str] = None


class ReferenceRequestChatRequest(BaseModel):
    message: str


class ReferenceRequestChatResponse(BaseModel):
    request: ReferenceRequestRead
    referee: RefereeRead
    assistant_reply: str
