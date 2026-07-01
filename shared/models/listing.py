from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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

    scores: Mapped[list["Score"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    applications: Mapped[list["Application"]] = relationship(back_populates="listing")  # noqa: F821


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    fit_breakdown: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    reasons: Mapped[Optional[str]] = mapped_column(Text)
    red_flags: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    model_used: Mapped[Optional[str]] = mapped_column(String(255))
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    listing: Mapped[Listing] = relationship(back_populates="scores")
