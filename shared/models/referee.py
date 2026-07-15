from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import Base, utcnow


class Referee(Base):
    __tablename__ = "referees"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_referees_user_id_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    institution: Mapped[Optional[str]] = mapped_column(String(512))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[Optional[str]] = mapped_column(String(64))  # advisor | collaborator | employer
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow, nullable=False)
