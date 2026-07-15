"""Dedupe stage — before spending on enrichment (AGENT.md §3.5).

A duplicate that reaches the enricher costs a page fetch plus a strong-model
call; catching it here costs string comparisons. Three checks, cheapest
first: canonical-URL exact match, in-batch repeats, then fuzzy
title+institution against the user's existing listings (same institution
only, ratio > 0.85). Matched originals get their last_seen refreshed.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from shared.llm import ExtractedListing
from shared.models import Listing
from shared.models.base import utcnow

log = logging.getLogger("phd_copilot.scraper.dedupe")

_TRACKING_PARAMS = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source")
FUZZY_THRESHOLD = 0.85


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip().lower()
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not any(k.lower().startswith(p) for p in _TRACKING_PARAMS)
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), "")
    )


def _identity(title: str | None, institution: str | None) -> tuple[str, str]:
    return ((title or "").strip().lower(), (institution or "").strip().lower())


def dedupe_listings(
    db: Session,
    user_id: int,
    listings: list[ExtractedListing],
) -> tuple[list[ExtractedListing], list[dict[str, Any]]]:
    """Returns (fresh, dupes). Dupes carry the title + what they matched."""

    existing = db.query(Listing.id, Listing.url, Listing.title, Listing.institution).filter(
        Listing.user_id == user_id
    ).all()
    existing_urls: dict[str, int] = {}
    by_institution: dict[str, list[tuple[str, int]]] = {}
    for row in existing:
        canon = canonicalize_url(row.url)
        if canon:
            existing_urls[canon] = row.id
        title_norm, inst_norm = _identity(row.title, row.institution)
        if title_norm:
            by_institution.setdefault(inst_norm, []).append((title_norm, row.id))

    fresh: list[ExtractedListing] = []
    dupes: list[dict[str, Any]] = []
    refresh_ids: set[int] = set()
    seen_urls: set[str] = set()
    seen_identities: set[tuple[str, str]] = set()

    for listing in listings:
        canon = canonicalize_url(listing.application_url)
        identity = _identity(listing.title, listing.institution)

        if canon and canon in existing_urls:
            dupes.append({"listing": listing.title, "matched": "existing url"})
            refresh_ids.add(existing_urls[canon])
            continue
        if canon and canon in seen_urls:
            dupes.append({"listing": listing.title, "matched": "same url in this run"})
            continue
        if identity[0] and identity in seen_identities:
            dupes.append({"listing": listing.title, "matched": "same title in this run"})
            continue

        fuzzy_hit = None
        if identity[0]:
            for title_norm, listing_id in by_institution.get(identity[1], []):
                if SequenceMatcher(None, identity[0], title_norm).ratio() > FUZZY_THRESHOLD:
                    fuzzy_hit = listing_id
                    break
        if fuzzy_hit is not None:
            dupes.append({"listing": listing.title, "matched": "existing listing (fuzzy title)"})
            refresh_ids.add(fuzzy_hit)
            continue

        if canon:
            seen_urls.add(canon)
        if identity[0]:
            seen_identities.add(identity)
        fresh.append(listing)

    if refresh_ids:
        db.query(Listing).filter(Listing.id.in_(refresh_ids)).update(
            {Listing.last_seen: utcnow()}, synchronize_session=False
        )
    if dupes:
        log.info("dedupe: %d duplicate(s) skipped before enrichment", len(dupes))
    return fresh, dupes
