from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, utcnow


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("user_id", "source", "source_key", name="uq_listings_user_source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1024))
    raw_path: Mapped[Optional[str]] = mapped_column(String(1024))

    title: Mapped[Optional[str]] = mapped_column(String(512))
    institution: Mapped[Optional[str]] = mapped_column(String(512))
    country: Mapped[Optional[str]] = mapped_column(String(128))
    city: Mapped[Optional[str]] = mapped_column(String(128))
    research_field: Mapped[Optional[str]] = mapped_column(String(255))
    offer_type: Mapped[Optional[str]] = mapped_column(String(128))
    funding_info: Mapped[Optional[str]] = mapped_column(Text)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    application_url: Mapped[Optional[str]] = mapped_column(String(1024))
    required_docs: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(Text)

    first_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    parsed_ok: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # passive_deletes=True on both: deleting a Listing must not try to null
    # out child FKs (they're NOT NULL) — defer entirely to each FK's
    # ON DELETE CASCADE in the database instead.
    scores: Mapped[list["Score"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", passive_deletes=True
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        back_populates="listing", passive_deletes=True
    )


class Score(Base):
    __tablename__ = "scores"
    # latest_score filters (user_id, listing_id) ordered by scored_at — the
    # hottest read in the app; the composite index serves it directly.
    __table_args__ = (Index("ix_scores_user_listing_scored_at", "user_id", "listing_id", "scored_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    fit_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    reasons: Mapped[Optional[str]] = mapped_column(Text)
    red_flags: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    model_used: Mapped[Optional[str]] = mapped_column(String(255))
    # Cached natural-language fit explanation (Phase 07). Written lazily by
    # GET /api/listings/:id/fit-explanation; nulled out if the score is
    # recomputed so a stale paragraph never survives a rescore.
    fit_paragraph: Mapped[Optional[str]] = mapped_column(Text)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    listing: Mapped[Listing] = relationship(back_populates="scores")
