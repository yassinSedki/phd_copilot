from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, utcnow


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    # queued|running|awaiting_continue|done|cancelled|failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    pages_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    listings_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    listings_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    # Serialized scraper state (current_url, page, all_listings, attempt) —
    # set only while status="awaiting_continue"; consumed by /continue.
    resume_state: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]]
