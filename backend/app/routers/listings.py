from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import User
from shared.repositories import listings as listing_repo
from app.schemas.listing import ListingDetail, ListingWithScore, ScoreRead

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingWithScore])
def list_listings(
    country: Optional[str] = None,
    field: Optional[str] = Query(None, alias="field"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("score", pattern="^(score|deadline)$"),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ListingWithScore]:
    rows = listing_repo.list_for_user(
        db,
        current_user.id,
        country=country,
        field=field,
        min_score=min_score,
        sort_by_score=(sort == "score"),
        limit=limit,
    )
    out: list[ListingWithScore] = []
    for listing, score in rows:
        item = ListingWithScore.model_validate(listing)
        if score is not None:
            item.latest_score = ScoreRead.model_validate(score)
        out.append(item)
    return out


@router.get("/{listing_id}", response_model=ListingDetail)
def get_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ListingDetail:
    listing = listing_repo.get_listing(db, current_user.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing not found")
    score = listing_repo.latest_score(db, current_user.id, listing_id)
    detail = ListingDetail.model_validate(listing)
    if score is not None:
        detail.latest_score = ScoreRead.model_validate(score)
    return detail
