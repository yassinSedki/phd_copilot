from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DeepDiveRequest(BaseModel):
    professor_name: str
    institution: Optional[str] = None
    lab_url: Optional[str] = None
    topic: Optional[str] = None
    personal_note: Optional[str] = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    professor_name: Optional[str] = None
    institution: Optional[str] = None
    lab_url: Optional[str] = None
    # Plain str on the READ path: this value comes from scraping, and strict
    # EmailStr validation here turns one malformed stored address into a 500
    # on every list/read. OutreachUpdate.email (user input) stays strict.
    email: Optional[str] = None
    research_summary: Optional[str] = None
    source_notes: Optional[str] = None
    publications: list[dict[str, Any]] = Field(default_factory=list)


class ChatTurn(BaseModel):
    role: str
    content: str


class OutreachRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_id: int
    draft_email: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    status: str
    sent_at: Optional[datetime] = None
    chat_history: list[ChatTurn] = Field(default_factory=list)
    created_at: datetime


class OutreachWithContact(BaseModel):
    outreach: OutreachRead
    contact: ContactRead


class OutreachChatRequest(BaseModel):
    message: str


class OutreachChatResponse(BaseModel):
    outreach: OutreachRead
    contact: ContactRead
    assistant_reply: str


class OutreachUpdate(BaseModel):
    draft_email: Optional[str] = None
    status: Optional[str] = None
    email: Optional[EmailStr] = None


class SaveEmailRequest(BaseModel):
    subject: str
    body: str
