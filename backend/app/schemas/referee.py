from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class RefereeCreate(BaseModel):
    name: str
    title: Optional[str] = None
    institution: Optional[str] = None
    email: EmailStr
    relationship_type: Optional[str] = None  # advisor | collaborator | employer
    notes: Optional[str] = None


class RefereeUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    institution: Optional[str] = None
    email: Optional[EmailStr] = None
    relationship_type: Optional[str] = None
    notes: Optional[str] = None


class RefereeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    title: Optional[str] = None
    institution: Optional[str] = None
    email: str
    relationship_type: Optional[str] = None
    notes: Optional[str] = None
    request_count: int = 0
    created_at: datetime
    updated_at: datetime
