from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import Document, Profile, User, UserSettings


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, email: str, password_hash: str) -> User:
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.add(UserSettings(user_id=user.id, score_threshold=70))
    db.commit()
    db.refresh(user)
    return user


def get_profile(db: Session, user_id: int) -> Optional[Profile]:
    return db.scalar(select(Profile).where(Profile.user_id == user_id))


def get_settings(db: Session, user_id: int) -> Optional[UserSettings]:
    return db.scalar(select(UserSettings).where(UserSettings.user_id == user_id))


def list_documents(db: Session, user_id: int) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.user_id == user_id)))
