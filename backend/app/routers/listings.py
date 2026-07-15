import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.config import get_settings
from shared.database import get_db
from shared.llm import get_llm
from shared.models import User
from shared.repositories import applications as app_repo
from shared.repositories import listings as listing_repo
from shared.repositories import users as users_repo
from app.schemas.listing import FitExplanation, ListingDetail, ListingRow, ListingWithScore, ScoreRead

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _funding_type(funding_info: Optional[str]) -> str:
    text = (funding_info or "").lower()
    if "fully funded" in text or "scholarship" in text or "fully-funded" in text:
        return "fully_funded"
    if "partial" in text:
        return "partial"
    return "unknown"


@router.get("", response_model=list[ListingRow])
def list_listings(
    country: Optional[str] = None,
    field: Optional[str] = Query(None, alias="field"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    sort: str = Query("score", pattern="^(score|deadline)$"),
    limit: int = Query(50, ge=1, le=500),
    search_run_id: Optional[int] = Query(
        None,
        description=(
            "Accepted for the /opportunities deep-link, but listings aren't "
            "linked to the search run that found them in the current schema "
            "— this is a no-op filter today. Add a search_run_id FK on "
            "Listing in a future phase to make it exact."
        ),
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ListingRow]:
    rows = listing_repo.list_for_user(
        db,
        current_user.id,
        country=country,
        field=field,
        min_score=min_score,
        sort_by_score=(sort == "score"),
        limit=limit,
    )
    out: list[ListingRow] = []
    for listing, score in rows:
        item = ListingRow.model_validate(listing)
        if score is not None:
            item.latest_score = ScoreRead.model_validate(score)
        item.funding_type = _funding_type(listing.funding_info)
        application = app_repo.get_by_listing(db, current_user.id, listing.id)
        if application is not None:
            item.status = application.status
            item.application_id = application.id
        out.append(item)
    return out


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not listing_repo.delete_listing(db, current_user.id, listing_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing not found")


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


@router.post("/{listing_id}/research", response_model=ListingDetail)
async def research_listing(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ListingDetail:
    """On-demand deep dive: fetch the listing's own page live, re-extract the
    full details with the LLM, and merge them into the stored row. Fills in
    what list-page scraping typically misses (full description, required
    documents, the real application URL, contact email)."""
    listing = listing_repo.get_listing(db, current_user.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing not found")

    # Prefer the OPPORTUNITY's own link. `url` can be the source list page /
    # university page the scrape started from — researching that produces
    # incoherent data (other listings' fields bleed in).
    url = listing.application_url or listing.url
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="listing has no URL to research")

    settings = get_settings()
    # Worker import kept local, mirroring the deepdive router — the backend
    # only pulls in scraper deps (bs4/playwright) when this path is hit.
    from worker.pipeline.ingest.scraper_graph import fetch_and_strip_page

    try:
        page_text = await fetch_and_strip_page(
            url,
            user_agent=settings.scraper_user_agent,
            playwright_enabled=settings.playwright_enabled,
        )
    except Exception:
        page_text = None
    if not page_text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="could not fetch the original listing page — try the original listing link directly",
        )

    # Blocking LLM network call — run in a worker thread so it doesn't
    # stall every other request on the event loop.
    llm = get_llm(settings.llm, role="builder")
    parsed = await asyncio.to_thread(llm.parse_listing, page_text)

    # Merge: the dedicated page is authoritative for content fields, but never
    # let a failed extraction null out data we already have. The deadline is
    # only taken when the row has none — parse_listing fabricates a +60-day
    # placeholder when the page omits it, which must not clobber a real date.
    listing.title = parsed.title or listing.title
    listing.institution = parsed.institution or listing.institution
    listing.country = parsed.country or listing.country
    listing.city = parsed.city or listing.city
    listing.research_field = parsed.research_field or listing.research_field
    listing.funding_info = parsed.funding_info or listing.funding_info
    listing.contact_email = parsed.contact_email or listing.contact_email
    listing.application_url = parsed.application_url or listing.application_url or url
    if parsed.required_docs:
        listing.required_docs = parsed.required_docs
    if parsed.description and len(parsed.description) > len(listing.description or ""):
        listing.description = parsed.description
    if listing.deadline is None:
        listing.deadline = parsed.deadline
    listing.parsed_ok = True
    db.commit()
    db.refresh(listing)

    score = listing_repo.latest_score(db, current_user.id, listing_id)
    detail = ListingDetail.model_validate(listing)
    if score is not None:
        detail.latest_score = ScoreRead.model_validate(score)
    return detail


@router.get("/{listing_id}/fit-explanation", response_model=FitExplanation)
def get_fit_explanation(
    listing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FitExplanation:
    listing = listing_repo.get_listing(db, current_user.id, listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing not found")
    score = listing_repo.latest_score(db, current_user.id, listing_id)
    if score is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing has not been scored yet")

    if score.fit_paragraph:
        return FitExplanation(paragraph=score.fit_paragraph)

    settings = get_settings()
    profile = users_repo.get_profile(db, current_user.id)
    llm = get_llm(settings.llm, role="drafter")
    paragraph = llm.explain_fit(
        {
            "full_name": profile.full_name if profile else None,
            "research_summary": profile.research_summary if profile else None,
            "interests": profile.interests if profile else None,
        },
        {
            "title": listing.title,
            "institution": listing.institution,
            "country": listing.country,
            "research_field": listing.research_field,
            "funding_info": listing.funding_info,
        },
        score.fit_breakdown or {},
        score.reasons or "",
        score.red_flags or [],
    )
    score.fit_paragraph = paragraph
    db.commit()
    return FitExplanation(paragraph=paragraph)
