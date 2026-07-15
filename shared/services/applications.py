from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from shared.models import Application, Listing
from shared.models.base import utcnow
from shared.repositories import applications as app_repo
from shared.repositories import listings as listing_repo
from shared.services import checklist as checklist_service
from shared.services import state_machine as sm


class ListingNotFound(Exception):
    pass


class AlreadyTracked(Exception):
    pass


def create_application(
    db: Session,
    *,
    user_id: int,
    listing_id: int,
    initial_status: str = sm.SAVED,
    priority: int = 0,
    notes: Optional[str] = None,
) -> Application:
    listing = listing_repo.get_listing(db, user_id, listing_id)
    if listing is None:
        raise ListingNotFound(f"listing {listing_id} not found")

    existing = app_repo.get_by_listing(db, user_id, listing_id)
    if existing is not None:
        raise AlreadyTracked(f"application already exists for listing {listing_id}")

    if initial_status not in sm.ALL_STATUSES:
        raise sm.IllegalTransition(f"unknown status: {initial_status}")

    application = Application(
        user_id=user_id,
        listing_id=listing.id,
        status=initial_status,
        priority=priority,
        deadline=listing.deadline,
        docs_checklist=checklist_service.derive_checklist(listing),
        notes=notes,
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent save raced past the existence check above — the DB
        # unique constraint is the authority.
        db.rollback()
        raise AlreadyTracked(f"application already exists for listing {listing_id}")
    db.refresh(application)
    return application


def update_application(
    db: Session,
    *,
    application: Application,
    status: Optional[str] = None,
    priority: Optional[int] = None,
    deadline: Optional[datetime] = None,
    notes: Optional[str] = None,
    next_action: Optional[str] = None,
    next_action_date: Optional[datetime] = None,
    commit: bool = True,
) -> Application:
    if status is not None and status != application.status:
        sm.check_transition(application.status, status, docs_checklist=application.docs_checklist)
        application.status = status
        if status == sm.APPLIED:
            application.applied_at = utcnow()

    if priority is not None:
        application.priority = priority
    if deadline is not None:
        application.deadline = deadline
    if notes is not None:
        application.notes = notes
    if next_action is not None:
        application.next_action = next_action
    if next_action_date is not None:
        application.next_action_date = next_action_date

    if commit:
        db.commit()
        db.refresh(application)
    return application


def update_docs(db: Session, *, application: Application, items: list[dict]) -> Application:
    application.docs_checklist = items
    db.commit()
    db.refresh(application)
    return application


class ChecklistItemNotFound(Exception):
    pass


def update_docs_item(db: Session, *, application: Application, item_id: str, fields: dict) -> Application:
    items = list(application.docs_checklist or [])
    for item in items:
        if item.get("id") == item_id:
            item.update(fields)
            break
    else:
        raise ChecklistItemNotFound(f"checklist item {item_id!r} not found")
    application.docs_checklist = items
    # `item.update(fields)` mutated the SAME dict objects `items` shares with
    # the column's current value, so by the time SQLAlchemy compares old vs.
    # new value at flush it sees no difference and silently skips the
    # UPDATE — the API call succeeds (200) but nothing is ever persisted.
    # flag_modified forces the column into the UPDATE regardless.
    flag_modified(application, "docs_checklist")
    db.commit()
    db.refresh(application)
    return application


def regenerate_checklist(db: Session, *, application: Application, listing: Listing) -> Application:
    application.docs_checklist = checklist_service.regenerate_preserving_ready(
        listing, application.docs_checklist
    )
    db.commit()
    db.refresh(application)
    return application


