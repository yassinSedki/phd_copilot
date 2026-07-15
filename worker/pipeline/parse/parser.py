"""Parse step: raw scraped text -> structured Listing fields via LLM.

Architecture section 8 step (2). The LLM client is pluggable; the stub gives
deterministic output good enough for end-to-end testing.
"""

from sqlalchemy.orm import Session

from shared.models import Listing
from shared.models.base import utcnow
from worker.pipeline.ingest.base import RawListing
from shared.llm import LLMClient


def upsert_listing(db: Session, user_id: int, raw: RawListing, raw_path: str | None = None) -> Listing:
    existing = (
        db.query(Listing)
        .filter(Listing.user_id == user_id, Listing.source == raw.source, Listing.source_key == raw.source_key)
        .one_or_none()
    )
    if existing is not None:
        existing.last_seen = utcnow()
        if raw_path:
            existing.raw_path = raw_path
        return existing

    listing = Listing(
        user_id=user_id,
        source=raw.source,
        source_key=raw.source_key,
        url=raw.url,
        raw_path=raw_path,
        parsed_ok=False,
    )
    db.add(listing)
    db.flush()
    return listing


def parse_listing(db: Session, llm: LLMClient, listing: Listing, raw_text: str) -> Listing:
    parsed = llm.parse_listing(raw_text)
    return apply_parsed(db, listing, parsed)


async def parse_listing_async(db: Session, llm: LLMClient, listing: Listing, raw_text: str) -> Listing:
    """LLM call off the event loop; Session mutations stay on the loop thread
    (SQLAlchemy sessions are not thread-safe)."""
    import asyncio

    parsed = await asyncio.to_thread(llm.parse_listing, raw_text)
    return apply_parsed(db, listing, parsed)


def apply_parsed(db: Session, listing: Listing, parsed) -> Listing:
    listing.title = parsed.title
    listing.institution = parsed.institution
    listing.country = parsed.country
    listing.city = parsed.city
    listing.research_field = parsed.research_field
    listing.offer_type = parsed.offer_type
    listing.funding_info = parsed.funding_info
    listing.deadline = parsed.deadline
    listing.contact_email = parsed.contact_email
    listing.application_url = parsed.application_url
    listing.required_docs = parsed.required_docs
    listing.description = parsed.description
    listing.parsed_ok = parsed.parsed_ok
    listing.last_seen = utcnow()
    db.flush()
    return listing
