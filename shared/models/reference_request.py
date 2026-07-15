from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, utcnow


class ReferenceRequest(Base):
    __tablename__ = "reference_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    referee_id: Mapped[int] = mapped_column(ForeignKey("referees.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")  # draft|sent|received|overdue
    submission_method: Mapped[str] = mapped_column(String(32), nullable=False)  # portal|forward_to_me|other
    email_subject: Mapped[Optional[str]] = mapped_column(String(512))
    email_body: Mapped[Optional[str]] = mapped_column(Text)
    # Ask-the-AI-to-revise conversation (Phase 13) — [{role, content}, ...].
    # Defaults to [] rather than NULL: ReferenceRequestRead.chat_history is a
    # non-nullable list, and a NULL row would 500 every list/get endpoint
    # (same landmine fixed on Outreach.chat_history).
    chat_history: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    sent_at: Mapped[Optional[datetime]]
    due_at: Mapped[Optional[datetime]]
    follow_up_at: Mapped[Optional[datetime]]

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
