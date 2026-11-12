"""Per-listing detail-page enrichment (the "card -> dedicated page" step).

The list page gives a lightweight, sometimes-noisy card per listing (title,
institution, a description snippet) because the LLM has to parse ALL
listings on the page in one call — crowding increases the chance of fields
getting conflated or dropped between listings. This step re-extracts each
*surviving* listing (post-prefilter, to avoid wasting fetches on ones that
were already going to be rejected) from its own dedicated page, where the
LLM only ever looks at one listing's content at a time.
"""

from __future__ import annotations

import asyncio
import logging

from shared.llm import ExtractedListing, LLMClient
from worker.pipeline.ingest.scraper_graph import fetch_and_strip_page

log = logging.getLogger("phd_copilot.scraper.detail")

# AGENT.md §3.6/§4.1: enrichment is the pipeline's dominant wall-clock cost —
# run detail fetches concurrently, bounded so we stay polite to the source.
ENRICH_CONCURRENCY = 4


def _same_page(a: str, b: str) -> bool:
    return a.rstrip("/").lower() == b.rstrip("/").lower()


async def enrich_listing(
    listing: ExtractedListing,
    llm: LLMClient,
    *,
    user_agent: str,
    playwright_enabled: bool = True,
    source_url: str | None = None,
) -> ExtractedListing:
    """Fetch `listing.application_url` (its own page) and re-extract full
    details from it. Falls back to the original card unchanged if there's no
    URL to fetch or the fetch/extraction fails — enrichment is best-effort,
    never a hard requirement for the pipeline to proceed."""

    url = listing.application_url
    if not url:
        log.info("enrich_listing: %r has no application_url — skipping detail fetch", listing.title)
        return listing
    if source_url and _same_page(url, source_url):
        # The "detail" URL is just the crowded list page we scraped — feeding
        # it back through single-listing extraction lets neighbouring
        # listings' fields bleed into this one. Card data is more coherent.
        log.info("enrich_listing: %r's application_url is the source list page — skipping detail fetch", listing.title)
        return listing

    try:
        detail_text = await fetch_and_strip_page(url, user_agent=user_agent, playwright_enabled=playwright_enabled)
    except Exception as exc:
        log.warning("enrich_listing: failed to fetch detail page %s: %s — keeping card data", url, exc)
        return listing

    if not detail_text:
        log.warning("enrich_listing: detail page %s returned no text — keeping card data", url)
        return listing

    # Blocking LLM network call — keep it off the event loop so other
    # enrichments' fetches can proceed concurrently.
    try:
        return await asyncio.to_thread(llm.extract_listing_detail, listing, detail_text[:20000], url)
    except Exception as exc:
        log.warning("enrich_listing: extraction failed for %s: %s — keeping card data", url, exc)
        return listing


async def enrich_listings(
    listings: list[ExtractedListing],
    llm: LLMClient,
    *,
    user_agent: str,
    playwright_enabled: bool = True,
    source_url: str | None = None,
) -> list[ExtractedListing]:
    """Enrich concurrently (bounded); order of the result matches the input.
    Each enrich is best-effort, so a failure just keeps that card's data."""

    semaphore = asyncio.Semaphore(ENRICH_CONCURRENCY)

    async def _bounded(listing: ExtractedListing) -> ExtractedListing:
        async with semaphore:
            return await enrich_listing(
                listing, llm, user_agent=user_agent, playwright_enabled=playwright_enabled, source_url=source_url
            )

    return list(await asyncio.gather(*(_bounded(lst) for lst in listings)))
