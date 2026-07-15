from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from shared.models import Application


def get(db: Session, user_id: int, application_id: int) -> Optional[Application]:
    return db.scalar(
        select(Application)
        .where(Application.id == application_id, Application.user_id == user_id)
        .options(selectinload(Application.listing))
    )


def get_by_listing(db: Session, user_id: int, listing_id: int) -> Optional[Application]:
    return db.scalar(
        select(Application).where(Application.user_id == user_id, Application.listing_id == listing_id)
    )


def list_for_user(db: Session, user_id: int) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.user_id == user_id)
            .options(selectinload(Application.listing))
            .order_by(Application.updated_at.desc())
        )
    )


def delete(db: Session, user_id: int, application_id: int) -> bool:
    """Deletes the application (scoped to the user) and, via ON DELETE
    CASCADE, its cover letter, document versions, and reference requests.
    The underlying Listing is untouched — only the tracking is removed.
    Returns False if not found."""
    app = get(db, user_id, application_id)
    if app is None:
        return False
    db.delete(app)
    db.commit()
    return True
