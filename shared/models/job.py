from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, utcnow


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    # queued|running|awaiting_continue|done|failed|cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_ref: Mapped[Optional[str]] = mapped_column(String(512))
    error: Mapped[Optional[str]] = mapped_column(Text)
    # Live status-panel detail: currently_checking, pages_processed,
    # listings_found, listings_kept_by_prefilter, listings_matched,
    # needs_continue_prompt, rendering. Nullable — old rows have none.
    progress_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
