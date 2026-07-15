from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, utcnow
from shared.models.listing import Listing


class Application(Base):
    __tablename__ = "applications"
    # One tracked application per listing per user — the service-level
    # check-then-insert alone is racy under concurrent saves.
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_applications_user_listing"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SAVED")
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    docs_checklist: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    cover_letter_path: Mapped[Optional[str]] = mapped_column(String(1024))
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_action: Mapped[Optional[str]] = mapped_column(String(512))
    next_action_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    listing: Mapped[Listing] = relationship(back_populates="applications")


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    body_markdown: Mapped[Optional[str]] = mapped_column(Text)
    chat_history: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    email_subject: Mapped[Optional[str]] = mapped_column(String(512))
    email_body: Mapped[Optional[str]] = mapped_column(Text)
    model_used: Mapped[Optional[str]] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    professor_name: Mapped[Optional[str]] = mapped_column(String(255))
    institution: Mapped[Optional[str]] = mapped_column(String(512))
    lab_url: Mapped[Optional[str]] = mapped_column(String(1024))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    research_summary: Mapped[Optional[str]] = mapped_column(Text)
    source_notes: Mapped[Optional[str]] = mapped_column(Text)
    # Structured mirror of the graph's research_topics/publications/overlaps
    # (Phase 11) — source_notes above stays as the original text dump, this
    # is what the frontend's generic-warning heuristic reads. Defaults to []
    # rather than NULL: ContactRead.publications is a non-nullable list, and
    # a NULL row 500s every read (same landmine already fixed on
    # Outreach.chat_history / ReferenceRequest.chat_history).
    publications: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)

    outreach: Mapped[list["Outreach"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    draft_email: Mapped[Optional[str]] = mapped_column(Text)
    email_subject: Mapped[Optional[str]] = mapped_column(String(512))
    email_body: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False)  # DRAFT|SENT
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # Ask-the-AI-to-revise conversation (Phase 13) — same shape as
    # DocumentVersion.chat_history: [{role, content}, ...]. Defaults to []
    # rather than NULL: OutreachRead.chat_history is a non-nullable list, and
    # rows created without an explicit value (e.g. the deep-dive task) used
    # to land as NULL and 500 every GET /outreach.
    chat_history: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    contact: Mapped[Contact] = relationship(back_populates="outreach")
