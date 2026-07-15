from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, utcnow


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("application_id", "doc_type", "version_number", name="uq_document_versions_app_type_ver"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )

    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)  # cover_letter|sop|research_proposal
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(16), nullable=False)  # user|agent
    # Chat history up to and including the turn that produced this version
    # (Phase 10 Task 7) — reverting to an older version resets chat to its
    # snapshot, which is the simplest correct behaviour without a separate
    # chat-history table.
    chat_history: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    author_notes: Mapped[Optional[str]] = mapped_column(Text)
    warnings: Mapped[Optional[list[Any]]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
