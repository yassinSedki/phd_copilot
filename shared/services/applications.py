from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from shared.models import Application, Listing
from shared.models.base import utcnow
from shared.repositories import applications as app_repo
from shared.repositories import listings as listing_repo
from shared.services import state_machine as sm


class ListingNotFound(Exception):
    pass


class AlreadyTracked(Exception):
    pass


def _docs_checklist_from_listing(listing: Listing) -> list[dict]:
    items: list[dict] = []
    for doc in listing.required_docs or []:
        if isinstance(doc, str):
            items.append({"doc": doc, "ready": False, "path": None})
        elif isinstance(doc, dict) and "doc" in doc:
            items.append({"doc": doc["doc"], "ready": bool(doc.get("ready")), "path": doc.get("path")})
    return items


def create_application(
    db: Session,
    *,
    user_id: int,
    listing_id: int,
    initial_status: str = sm.REVIEWING,
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
        docs_checklist=_docs_checklist_from_listing(listing),
        notes=notes,
    )
    db.add(application)
    db.commit()
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

    db.commit()
    db.refresh(application)
    return application


def update_docs(db: Session, *, application: Application, items: list[dict]) -> Application:
    application.docs_checklist = items
    db.commit()
    db.refresh(application)
    return application


def expire_overdue(db: Session, user_id: int) -> int:
    """Mark applications past deadline (and not yet APPLIED) as EXPIRED."""
    now = utcnow()
    count = 0
    for app in app_repo.list_for_user(db, user_id):
        if app.deadline and app.deadline < now and app.status not in {
            sm.APPLIED, sm.INTERVIEW, sm.OFFER, sm.REJECTED, sm.WITHDRAWN, sm.EXPIRED,
        }:
            app.status = sm.EXPIRED
            count += 1
    if count:
        db.commit()
    return count
