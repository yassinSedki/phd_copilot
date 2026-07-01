from typing import Optional

from sqlalchemy import desc, select
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
    subq = (
        select(Score)
        .where(Score.user_id == user_id)
        .order_by(Score.listing_id, desc(Score.scored_at))
        .subquery()
    )
    stmt = select(Listing).where(Listing.user_id == user_id)
    if country:
        stmt = stmt.where(Listing.country == country)
    if field:
        stmt = stmt.where(Listing.research_field == field)
    listings = list(db.scalars(stmt.limit(limit * 4)))
    results: list[tuple[Listing, Optional[Score]]] = []
    for listing in listings:
        score = db.scalar(
            select(Score)
            .where(Score.listing_id == listing.id, Score.user_id == user_id)
            .order_by(desc(Score.scored_at))
            .limit(1)
        )
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
