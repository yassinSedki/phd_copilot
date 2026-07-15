"""Hybrid prefilter — the cost-control heart of the pipeline (AGENT.md §3.4).

Two passes, cheapest first:

Pass A — embeddings (near-free): cosine similarity between the user's
profile digest and each listing's title+snippet. Obviously-unrelated
listings are auto-discarded, obviously-related ones auto-kept; only the
uncertain middle band pays for an LLM call.

Pass B — cheap LLM, BATCHED (20 records per call instead of one call per
listing): recall-biased — reject only on a clear hard-constraint violation,
keep on doubt. A false discard is invisible and unrecoverable; a false keep
costs one page fetch.
"""

from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Optional

from shared.llm import ExtractedListing, LLMClient
from shared.llm.jsonx import extract_json_object
from shared.llm.prompts import prefilter_listing as prefilter_prompt

log = logging.getLogger("phd_copilot.scraper.prefilter")

# Pass A thresholds (AGENT.md §3.4)
SIM_DISCARD = 0.30
SIM_KEEP = 0.62
LLM_BATCH_SIZE = 20


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _listing_text(listing: ExtractedListing) -> str:
    snippet = (listing.description or "")[:300]
    return f"{listing.title or ''}. {listing.research_field or ''}. {snippet}".strip()


async def _embedding_pass(
    embeddings: Any,
    profile_text: str,
    listings: list[ExtractedListing],
) -> tuple[list[ExtractedListing], list[dict[str, Any]], list[ExtractedListing]]:
    """Returns (auto_kept, auto_dropped, uncertain). On any provider failure
    the whole batch is 'uncertain' — never lose a listing to a flaky call."""

    try:
        profile_vec = await embeddings.embed(profile_text[:2000], input_type="search_query")
        vecs = await embeddings.embed_batch([_listing_text(l) for l in listings])
    except Exception as exc:
        log.warning("prefilter pass A skipped (embedding failure): %s", exc)
        return [], [], list(listings)

    kept: list[ExtractedListing] = []
    dropped: list[dict[str, Any]] = []
    uncertain: list[ExtractedListing] = []
    for listing, vec in zip(listings, vecs):
        # A near-empty record (extraction lost the title/snippet) carries no
        # embedding signal — low cosine there means "no text", not
        # "unrelated". Send it to the LLM pass instead of discarding.
        if len(_listing_text(listing)) < 40:
            uncertain.append(listing)
            continue
        sim = _cosine(profile_vec, vec)
        if sim < SIM_DISCARD:
            dropped.append(
                {"listing": listing.title, "reason": f"unrelated to profile (similarity {sim:.2f})", "stage": "embedding"}
            )
        elif sim > SIM_KEEP:
            kept.append(listing)
        else:
            uncertain.append(listing)
    return kept, dropped, uncertain


async def _llm_pass(
    llm: LLMClient,
    constraints: dict[str, Any],
    profile_digest: str,
    listings: list[ExtractedListing],
) -> tuple[list[ExtractedListing], list[dict[str, Any]]]:
    """Batched cheap-LLM decisions, 20 records per call. Fail open per batch.
    The provider call is blocking network I/O — run it off the event loop."""

    kept: list[ExtractedListing] = []
    dropped: list[dict[str, Any]] = []
    for start in range(0, len(listings), LLM_BATCH_SIZE):
        batch = listings[start : start + LLM_BATCH_SIZE]
        records = [
            {
                "id": i,
                "title": l.title,
                "institution": l.institution,
                "location": l.city or l.country,
                "snippet": (l.description or "")[:400],
            }
            for i, l in enumerate(batch)
        ]
        try:
            out = await asyncio.to_thread(
                llm.invoke,
                [
                    {"role": "system", "content": prefilter_prompt.SYSTEM_BATCH},
                    {"role": "user", "content": prefilter_prompt.build_batch_user(constraints, profile_digest, records)},
                ],
                json_mode=True,
            )
            decisions = {
                int(d["id"]): d
                for d in extract_json_object(out).get("decisions", [])
                if isinstance(d, dict) and "id" in d
            }
        except Exception as exc:  # fail open — never lose a real match to a flaky call
            log.warning("prefilter batch failed, keeping all %d: %s", len(batch), exc)
            kept.extend(batch)
            continue

        for i, listing in enumerate(batch):
            decision = decisions.get(i)
            # Missing decision for an id → keep (recall bias).
            if decision is None or decision.get("keep", True):
                kept.append(listing)
            else:
                dropped.append({"listing": listing.title, "reason": decision.get("reason", ""), "stage": "llm"})
    return kept, dropped


async def prefilter_batch(
    llm: LLMClient,
    constraints: dict[str, Any],
    extracted_listings: list[ExtractedListing],
    *,
    profile_digest: str = "",
    embeddings: Optional[Any] = None,
) -> tuple[list[ExtractedListing], list[dict[str, Any]]]:
    """Returns (kept, dropped). `dropped` entries carry the listing + reason +
    the stage that dropped it, for surfacing in the progress panel."""

    if not constraints and not profile_digest:
        return list(extracted_listings), []

    remaining = list(extracted_listings)
    kept: list[ExtractedListing] = []
    dropped: list[dict[str, Any]] = []

    if embeddings is not None and profile_digest:
        auto_kept, auto_dropped, remaining = await _embedding_pass(embeddings, profile_digest, remaining)
        kept.extend(auto_kept)
        dropped.extend(auto_dropped)
        log.info(
            "prefilter pass A: %d auto-kept, %d auto-dropped, %d to LLM",
            len(auto_kept), len(auto_dropped), len(remaining),
        )

    if remaining:
        if constraints or profile_digest:
            llm_kept, llm_dropped = await _llm_pass(llm, constraints, profile_digest, remaining)
            kept.extend(llm_kept)
            dropped.extend(llm_dropped)
        else:
            kept.extend(remaining)

    return kept, dropped
