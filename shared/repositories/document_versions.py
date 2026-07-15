from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from shared.models import DocumentVersion


def list_by_user(db: Session, user_id: int) -> list[DocumentVersion]:
    return list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.user_id == user_id)
            .order_by(DocumentVersion.created_at.desc())
        )
    )


def get(db: Session, id: int, user_id: int) -> Optional[DocumentVersion]:
    return db.scalar(select(DocumentVersion).where(DocumentVersion.id == id, DocumentVersion.user_id == user_id))


def create(db: Session, user_id: int, **fields) -> DocumentVersion:
    version = DocumentVersion(user_id=user_id, **fields)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update(db: Session, id: int, user_id: int, **fields) -> Optional[DocumentVersion]:
    version = get(db, id, user_id)
    if version is None:
        return None
    for key, value in fields.items():
        setattr(version, key, value)
    db.commit()
    db.refresh(version)
    return version


def delete(db: Session, id: int, user_id: int) -> None:
    version = get(db, id, user_id)
    if version is not None:
        db.delete(version)
        db.commit()


def list_for_document(db: Session, user_id: int, application_id: int, doc_type: str) -> list[DocumentVersion]:
    return list(
        db.scalars(
            select(DocumentVersion)
            .where(
                DocumentVersion.user_id == user_id,
                DocumentVersion.application_id == application_id,
                DocumentVersion.doc_type == doc_type,
            )
            .order_by(desc(DocumentVersion.version_number))
        )
    )


def get_latest(db: Session, user_id: int, application_id: int, doc_type: str) -> Optional[DocumentVersion]:
    return db.scalar(
        select(DocumentVersion)
        .where(
            DocumentVersion.user_id == user_id,
            DocumentVersion.application_id == application_id,
            DocumentVersion.doc_type == doc_type,
        )
        .order_by(desc(DocumentVersion.version_number))
        .limit(1)
    )
