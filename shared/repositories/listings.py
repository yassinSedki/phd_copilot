from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from shared.models import Listing, Score


def get_listing(db: Session, user_id: int, listing_id: int) -> Optional[Listing]:
    return db.scalar(select(Listing).where(Listing.id == listing_id, Listing.user_id == user_id))


def get_by_source_key(db: Session, user_id: int, source: str, source_key: str) -> Optional[Listing]:
    return db.scalar(
        select(Listing).where(
            Listing.user_id == user_id,
            Listing.source == source,
            Listing.source_key == source_key,
        )
    )


def list_for_user(
    db: Session,
    user_id: int,
    *,
    country: Optional[str] = None,
    field: Optional[str] = None,
    min_score: Optional[float] = None,
    sort_by_score: bool = True,
    limit: int = 100,
) -> list[tuple[Listing, Optional[Score]]]:
    stmt = select(Listing).where(Listing.user_id == user_id)
    if country:
        stmt = stmt.where(Listing.country == country)
    if field:
        stmt = stmt.where(Listing.research_field == field)
    listings = list(db.scalars(stmt.limit(limit * 4)))
    if not listings:
        return []

    # Latest score per listing via one row_number window query instead of a
    # per-listing lookup — the old loop was O(rows) queries.
    ranked = (
        select(
            Score.id.label("score_id"),
            func.row_number()
            .over(partition_by=Score.listing_id, order_by=desc(Score.scored_at))
            .label("rn"),
        )
        .where(Score.user_id == user_id, Score.listing_id.in_([lst.id for lst in listings]))
        .subquery()
    )
    latest_ids = list(db.scalars(select(ranked.c.score_id).where(ranked.c.rn == 1)))
    latest = {
        s.listing_id: s
        for s in db.scalars(select(Score).where(Score.id.in_(latest_ids)))
    } if latest_ids else {}

    results: list[tuple[Listing, Optional[Score]]] = []
    for listing in listings:
        score = latest.get(listing.id)
        if min_score is not None and (score is None or score.score < min_score):
            continue
        results.append((listing, score))
    if sort_by_score:
        results.sort(key=lambda x: (x[1].score if x[1] else -1), reverse=True)
    return results[:limit]


def latest_score(db: Session, user_id: int, listing_id: int) -> Optional[Score]:
    return db.scalar(
        select(Score)
        .where(Score.listing_id == listing_id, Score.user_id == user_id)
        .order_by(desc(Score.scored_at))
        .limit(1)
    )


def delete_listing(db: Session, user_id: int, listing_id: int) -> bool:
    """Deletes the listing (scoped to the user) and, via ON DELETE CASCADE,
    its scores and any tracked application (+ that application's cover
    letters, documents, reference requests). Returns False if not found."""
    listing = get_listing(db, user_id, listing_id)
    if listing is None:
        return False
    db.delete(listing)
    db.commit()
    return True
