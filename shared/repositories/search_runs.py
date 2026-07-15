from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import SearchRun


def list_by_user(db: Session, user_id: int) -> list[SearchRun]:
    return list(db.scalars(select(SearchRun).where(SearchRun.user_id == user_id).order_by(SearchRun.created_at.desc())))


def get(db: Session, id: int, user_id: int) -> Optional[SearchRun]:
    return db.scalar(select(SearchRun).where(SearchRun.id == id, SearchRun.user_id == user_id))


def create(db: Session, user_id: int, **fields) -> SearchRun:
    run = SearchRun(user_id=user_id, **fields)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update(db: Session, id: int, user_id: int, **fields) -> Optional[SearchRun]:
    run = get(db, id, user_id)
    if run is None:
        return None
    for key, value in fields.items():
        setattr(run, key, value)
    db.commit()
    db.refresh(run)
    return run


def delete(db: Session, id: int, user_id: int) -> None:
    run = get(db, id, user_id)
    if run is not None:
        db.delete(run)
        db.commit()
