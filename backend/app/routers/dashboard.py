from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import Application, Job, Listing, User
from shared.models.base import utcnow
from shared.repositories import applications as app_repo
from shared.repositories import listings as listing_repo
from app.schemas.application import ApplicationRead
from app.schemas.dashboard import DashboardResponse
from app.schemas.listing import ListingWithScore, ScoreRead
from shared.services import state_machine as sm

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    user_id = current_user.id

    counts_rows = db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.user_id == user_id)
        .group_by(Application.status)
    ).all()
    counts_by_status = {status: 0 for status in sm.KANBAN_COLUMNS}
    for status, count in counts_rows:
        counts_by_status[status] = count

    top_rows = listing_repo.list_for_user(db, user_id, sort_by_score=True, limit=5)
    top_matches: list[ListingWithScore] = []
    for listing, score in top_rows:
        item = ListingWithScore.model_validate(listing)
        if score is not None:
            item.latest_score = ScoreRead.model_validate(score)
        top_matches.append(item)

    apps = app_repo.list_for_user(db, user_id)
    now = utcnow()
    soon = now + timedelta(days=21)

    upcoming = sorted(
        [
            a for a in apps
            if a.deadline is not None
            and a.deadline >= now
            and a.deadline <= soon
            and a.status not in {sm.APPLIED, sm.REJECTED, sm.WITHDRAWN, sm.EXPIRED}
        ],
        key=lambda a: a.deadline,
    )[:8]

    action_needed = [
        a for a in apps if a.status in {sm.READY, sm.DRAFTING}
    ][:8]

    in_progress = [
        a for a in apps if a.status in {sm.REVIEWING, sm.SHORTLISTED}
    ][:8]

    total_listings = db.scalar(select(func.count(Listing.id)).where(Listing.user_id == user_id)) or 0
    total_applications = sum(counts_by_status.values())

    last_run = db.scalar(
        select(Job)
        .where(Job.user_id == user_id, Job.type == "run_pipeline", Job.status == "done")
        .order_by(desc(Job.finished_at))
        .limit(1)
    )
    last_run_at = last_run.finished_at.isoformat() if last_run and last_run.finished_at else None

    return DashboardResponse(
        counts_by_status=counts_by_status,
        top_matches=top_matches,
        upcoming_deadlines=[ApplicationRead.model_validate(a) for a in upcoming],
        action_needed=[ApplicationRead.model_validate(a) for a in action_needed],
        in_progress=[ApplicationRead.model_validate(a) for a in in_progress],
        total_listings=total_listings,
        total_applications=total_applications,
        last_run_at=last_run_at,
    )
