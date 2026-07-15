from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import Referee


def list_by_user(db: Session, user_id: int) -> list[Referee]:
    return list(db.scalars(select(Referee).where(Referee.user_id == user_id).order_by(Referee.name)))


def get(db: Session, id: int, user_id: int) -> Optional[Referee]:
    return db.scalar(select(Referee).where(Referee.id == id, Referee.user_id == user_id))


def create(db: Session, user_id: int, **fields) -> Referee:
    referee = Referee(user_id=user_id, **fields)
    db.add(referee)
    db.commit()
    db.refresh(referee)
    return referee


def update(db: Session, id: int, user_id: int, **fields) -> Optional[Referee]:
    referee = get(db, id, user_id)
    if referee is None:
        return None
    for key, value in fields.items():
        setattr(referee, key, value)
    db.commit()
    db.refresh(referee)
    return referee


def delete(db: Session, id: int, user_id: int) -> None:
    referee = get(db, id, user_id)
    if referee is not None:
        db.delete(referee)
        db.commit()
