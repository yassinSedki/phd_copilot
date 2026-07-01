from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    at: Optional[datetime] = None


class CoverLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    application_id: int
    body_markdown: Optional[str] = None
    chat_history: list[ChatTurn] = Field(default_factory=list)
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    model_used: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CoverLetterChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class CoverLetterChatResponse(BaseModel):
    letter: CoverLetterRead
    assistant_reply: str
