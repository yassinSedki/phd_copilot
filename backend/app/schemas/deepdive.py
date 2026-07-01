from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class DeepDiveRequest(BaseModel):
    professor_name: str
    institution: Optional[str] = None
    lab_url: Optional[str] = None
    topic: Optional[str] = None


class ContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    professor_name: Optional[str] = None
    institution: Optional[str] = None
    lab_url: Optional[str] = None
    email: Optional[EmailStr] = None
    research_summary: Optional[str] = None
    source_notes: Optional[str] = None


class OutreachRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_id: int
    draft_email: Optional[str] = None
    status: str
    created_at: datetime


class OutreachWithContact(BaseModel):
    outreach: OutreachRead
    contact: ContactRead


class OutreachUpdate(BaseModel):
    draft_email: Optional[str] = None
    status: Optional[str] = None
    email: Optional[EmailStr] = None
