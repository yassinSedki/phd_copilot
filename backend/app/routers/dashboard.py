from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    FeaturedOpportunity,
    LastRun,
    NextAction,
    PipelineStage,
    RecentSearchItem,
    UrgencyCta,
    UrgencyItem,
)
from app.services import reference_requests as ref_service
from shared.database import get_db
from shared.models import Application, Listing, Score, SearchRun, User
from shared.models.base import utcnow
from shared.repositories import applications as app_repo
from shared.repositories import users as users_repo
from shared.services import state_machine as sm

router = APIRouter(prefix="/api", tags=["dashboard"])

MAX_URGENT = 8
DEADLINE_WINDOW_DAYS = 21
REFERENCE_DUE_SOON_DAYS = 10
EXCELLENT_MATCH_SCORE = 85

# Pipeline stage order — mirrors the real application status machine
# (shared/services/state_machine.py). "Found" isn't a status; it's every
# discovered listing that was never saved into the tracker at all.
_PIPELINE_STAGES = [
    ("found", "Found"),
    (sm.SAVED, "Saved"),
    (sm.IN_PROGRESS, "In progress"),
    (sm.DOCS_READY, "Docs ready"),
    (sm.APPLIED, "Applied"),
    (sm.INTERVIEW, "Interview"),
    (sm.OFFER, "Offer"),
]


def _funding_type(funding_info: Optional[str]) -> str:
    text = (funding_info or "").lower()
    if "fully funded" in text or "scholarship" in text or "fully-funded" in text:
        return "fully_funded"
    if "partial" in text:
        return "partial"
    return "unknown"


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardResponse:
    user_id = current_user.id
    now = utcnow()

    urgent: list[UrgencyItem] = []

    apps = app_repo.list_for_user(db, user_id)
    inactive = {sm.APPLIED, sm.INTERVIEW, sm.OFFER, sm.REJECTED, sm.WITHDRAWN}

    for a in apps:
        if a.deadline and a.status not in inactive:
            days_until = (a.deadline - now).days
            if 0 <= days_until <= DEADLINE_WINDOW_DAYS:
                urgent.append(
                    UrgencyItem(
                        kind="deadline_near",
                        application_id=a.id,
                        title=a.listing.title or "Untitled",
                        institution=a.listing.institution,
                        days_until=days_until,
                        cta=UrgencyCta(label="Open application", href=f"/tracker/{a.id}"),
                    )
                )
        if a.status == sm.IN_PROGRESS:
            urgent.append(
                UrgencyItem(
                    kind="letter_ready_to_send",
                    application_id=a.id,
                    title=a.listing.title or "Untitled",
                    institution=a.listing.institution,
                    days_until=(a.deadline - now).days if a.deadline else 999,
                    cta=UrgencyCta(label="Finish letter", href=f"/tracker/{a.id}/letter"),
                )
            )
        if a.status == sm.DOCS_READY:
            urgent.append(
                UrgencyItem(
                    kind="letter_ready_to_send",
                    application_id=a.id,
                    title=a.listing.title or "Untitled",
                    institution=a.listing.institution,
                    days_until=(a.deadline - now).days if a.deadline else 999,
                    cta=UrgencyCta(label="Ready to send", href=f"/tracker/{a.id}"),
                )
            )

    # Piggybacks the overdue sweep on this request (Phase 12 brief: "no cron
    # needed") — flips any past-due "sent" request to "overdue" first.
    for r in ref_service.check_overdue_and_due_soon(db, user_id):
        if r.status == "overdue":
            urgent.append(
                UrgencyItem(
                    kind="reference_overdue",
                    application_id=r.application_id,
                    title="Reference letter overdue",
                    institution=None,
                    days_until=(r.due_at - now).days if r.due_at else -1,
                    cta=UrgencyCta(label="Follow up", href=f"/referees?request_id={r.id}"),
                )
            )
        else:
            days_until = (r.due_at - now).days if r.due_at else REFERENCE_DUE_SOON_DAYS
            urgent.append(
                UrgencyItem(
                    kind="reference_due_soon",
                    application_id=r.application_id,
                    title="Reference letter due soon",
                    institution=None,
                    days_until=days_until,
                    cta=UrgencyCta(label="Remind referee", href=f"/referees?request_id={r.id}"),
                )
            )

    upcoming_deadlines_count = sum(1 for u in urgent if u.kind == "deadline_near")

    urgent.sort(key=lambda u: u.days_until)
    urgent = urgent[:MAX_URGENT]

    # ---- Real aggregates: opportunities, latest score per listing, pipeline ----
    opportunities_count = db.scalar(select(func.count()).select_from(Listing).where(Listing.user_id == user_id)) or 0

    latest_scored_at = (
        select(Score.listing_id, func.max(Score.scored_at).label("max_at"))
        .where(Score.user_id == user_id)
        .group_by(Score.listing_id)
        .subquery()
    )
    latest_pairs = db.execute(
        select(Listing, Score)
        .join(Score, Score.listing_id == Listing.id)
        .join(
            latest_scored_at,
            (Score.listing_id == latest_scored_at.c.listing_id) & (Score.scored_at == latest_scored_at.c.max_at),
        )
        .where(Listing.user_id == user_id)
    ).all()

    avg_match = round(sum(s.score for _, s in latest_pairs) / len(latest_pairs), 1) if latest_pairs else None

    apps_by_listing = {a.listing_id: a for a in apps}
    terminal_or_committed = {sm.APPLIED, sm.INTERVIEW, sm.OFFER, sm.REJECTED, sm.WITHDRAWN}
    still_actionable = [
        (listing, score)
        for listing, score in latest_pairs
        if apps_by_listing.get(listing.id) is None or apps_by_listing[listing.id].status not in terminal_or_committed
    ]
    featured: Optional[FeaturedOpportunity] = None
    if still_actionable:
        top_listing, top_score = max(still_actionable, key=lambda pair: pair[1].score)
        top_app = apps_by_listing.get(top_listing.id)
        days_left = (top_listing.deadline - now).days if top_listing.deadline else None
        featured = FeaturedOpportunity(
            listing_id=top_listing.id,
            application_id=top_app.id if top_app else None,
            title=top_listing.title or "Untitled",
            institution=top_listing.institution,
            score=top_score.score,
            funding_type=_funding_type(top_listing.funding_info),
            deadline=top_listing.deadline.isoformat() if top_listing.deadline else None,
            days_until_deadline=days_left,
        )

    status_counts: dict[str, int] = {}
    for a in apps:
        status_counts[a.status] = status_counts.get(a.status, 0) + 1
    tracked_listing_ids = set(apps_by_listing.keys())
    found_count = max(0, opportunities_count - len(tracked_listing_ids))
    pipeline = [
        PipelineStage(key=key, label=label, count=found_count if key == "found" else status_counts.get(key, 0))
        for key, label in _PIPELINE_STAGES
    ]

    stats = DashboardStats(
        opportunities=opportunities_count,
        avg_match=avg_match,
        applications=len(apps),
        interviews=status_counts.get(sm.INTERVIEW, 0),
        offers=status_counts.get(sm.OFFER, 0),
        upcoming_deadlines=upcoming_deadlines_count,
        excellent_matches=sum(1 for _, s in latest_pairs if s.score >= EXCELLENT_MATCH_SCORE),
    )

    # ---- Next actions: real, derived from the same signals as `urgent`,
    # plus a profile-completeness nudge — never invented busywork. ----
    next_actions: list[NextAction] = []
    for u in urgent[:4]:
        next_actions.append(NextAction(label=f"{u.cta.label}: {u.title}", href=u.cta.href, kind=(
            "deadline" if u.kind == "deadline_near"
            else "docs" if u.kind == "letter_ready_to_send"
            else "reference"
        )))
    profile = users_repo.get_profile(db, user_id)
    if not profile or not profile.cv_filename:
        next_actions.append(NextAction(label="Upload your CV to improve matching", href="/settings", kind="cv"))
    elif not profile.research_summary:
        next_actions.append(NextAction(label="Write your research summary", href="/settings", kind="cv"))
    next_actions = next_actions[:5]

    recent_rows = db.scalars(
        select(SearchRun)
        .where(SearchRun.user_id == user_id)
        .order_by(desc(SearchRun.created_at))
        .limit(5)
    ).all()
    recent_searches = [
        RecentSearchItem(
            id=r.id,
            url=r.url,
            status=r.status,
            listings_matched=r.listings_matched,
            created_at=r.created_at.isoformat(),
        )
        for r in recent_rows
    ]

    last_done = db.scalar(
        select(SearchRun)
        .where(SearchRun.user_id == user_id, SearchRun.status == "done")
        .order_by(desc(SearchRun.finished_at))
        .limit(1)
    )
    if last_done is not None:
        last_run = LastRun(
            search_run_id=last_done.id,
            finished_at=last_done.finished_at.isoformat() if last_done.finished_at else None,
            listings_matched=last_done.listings_matched,
            summary=f"Found {last_done.listings_found}, matched {last_done.listings_matched}",
        )
    else:
        last_run = LastRun(summary="No searches yet.")

    return DashboardResponse(
        urgent=urgent,
        recent_searches=recent_searches,
        last_run=last_run,
        stats=stats,
        pipeline=pipeline,
        featured=featured,
        next_actions=next_actions,
    )
