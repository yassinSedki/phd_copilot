from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import ReferenceRequest


def list_by_user(db: Session, user_id: int) -> list[ReferenceRequest]:
    return list(
        db.scalars(
            select(ReferenceRequest)
            .where(ReferenceRequest.user_id == user_id)
            .order_by(ReferenceRequest.created_at.desc())
        )
    )


def get(db: Session, id: int, user_id: int) -> Optional[ReferenceRequest]:
    return db.scalar(select(ReferenceRequest).where(ReferenceRequest.id == id, ReferenceRequest.user_id == user_id))


def create(db: Session, user_id: int, **fields) -> ReferenceRequest:
    request = ReferenceRequest(user_id=user_id, **fields)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def update(db: Session, id: int, user_id: int, **fields) -> Optional[ReferenceRequest]:
    request = get(db, id, user_id)
    if request is None:
        return None
    for key, value in fields.items():
        setattr(request, key, value)
    db.commit()
    db.refresh(request)
    return request


def delete(db: Session, id: int, user_id: int) -> None:
    request = get(db, id, user_id)
    if request is not None:
        db.delete(request)
        db.commit()
