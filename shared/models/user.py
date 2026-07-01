from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped[Optional["Profile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    settings: Mapped[Optional["UserSettings"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_profiles_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    research_summary: Mapped[Optional[str]] = mapped_column(Text)
    interests: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    education: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    publications: Mapped[Optional[list[Any]]] = mapped_column(JSON)
    languages: Mapped[Optional[str]] = mapped_column(String(255))
    location_prefs: Mapped[Optional[str]] = mapped_column(String(255))
    constraints: Mapped[Optional[str]] = mapped_column(Text)
    cv_path: Mapped[Optional[str]] = mapped_column(String(512))
    cv_text: Mapped[Optional[str]] = mapped_column(Text)
    cv_filename: Mapped[Optional[str]] = mapped_column(String(255))
    cv_sha256: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    user: Mapped[User] = relationship(back_populates="profile")


class UserSettings(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_settings_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    filters: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    score_threshold: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    scoring_model: Mapped[Optional[str]] = mapped_column(String(255))
    drafting_model: Mapped[Optional[str]] = mapped_column(String(255))
    schedule: Mapped[Optional[str]] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="settings")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)

    user: Mapped[User] = relationship(back_populates="documents")
