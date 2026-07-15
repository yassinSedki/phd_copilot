"""run_pipeline_url: scrape ANY URL → prefilter → parse → score → auto-create apps.

Architecture: phd copilot.md → scraper-agent diagram + "Batch processing
with live progress". Listings are processed in batches of BATCH_SIZE
(default 5) and `jobs.progress` is updated after each batch so the UI
gets near-live feedback.

Phase 04: pre-filter extracted listings against the user's hard constraints
before parse+score, persist a SearchRun row per URL run, and support a
human-in-the-loop pagination checkpoint (pause after N pages, resume via
`resume_state`, or cancel).
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.database import SessionLocal
from shared.models import Listing
from shared.repositories import applications as app_repo
from shared.repositories import jobs as jobs_repo
from shared.repositories import search_runs as search_runs_repo
from shared.repositories import users as users_repo
from shared.services import applications as app_service
from shared.services import state_machine as sm
from worker.pipeline.ingest import run_scraper_graph
from worker.pipeline.ingest.base import RawListing
from worker.pipeline.ingest.dedupe import dedupe_listings
from worker.pipeline.ingest.detail_fetch import enrich_listings
from worker.pipeline.ingest.prefilter import prefilter_batch
from shared.llm import ExtractedListing, get_llm
from worker.pipeline.parse.parser import parse_listing, parse_listing_async, upsert_listing
from worker.pipeline.score.scorer import score_listing, score_listing_async

log = logging.getLogger("phd_copilot.pipeline")

PAGES_BEFORE_PAUSE = 3


def _extracted_to_raw(extracted: ExtractedListing, url: str) -> RawListing:
    # Encode the extracted dict into a key/value text block — the parser
    # picks fields back out (whether stub regex or Claude JSON extract).
    blob = "\n".join(
        f"{k}: {v}"
        for k, v in {
            "title": extracted.title,
            "institution": extracted.institution,
            "country": extracted.country,
            "city": extracted.city,
            "field": extracted.research_field,
            "offer_type": extracted.offer_type,
            "funding": extracted.funding_info,
            "deadline": extracted.deadline_text,
            "contact_email": extracted.contact_email,
            "application_url": extracted.application_url,
            # Enrichment extracts these from the listing's own page; the
            # parser picks them back out of the blob. (This used to be
            # hardcoded "" — which silently emptied every checklist.)
            "required_docs": ", ".join(extracted.required_docs or []),
            "description": (extracted.description or "")[:4000],
        }.items()
        if v
    )
    return RawListing(
        source="url",
        source_key=extracted.source_key or f"{url}#{extracted.title or 'untitled'}",
        url=extracted.application_url or url,
        raw_text=blob,
    )


def _profile_digest(profile: Any) -> str:
    """Compressed ~120-word profile paragraph for prefiltering (AGENT.md §4.2)
    — the full profile is only ever sent to the scorer."""
    if profile is None:
        return ""
    parts = [
        profile.research_summary or "",
        ", ".join(profile.interests or []) if isinstance(profile.interests, list) else str(profile.interests or ""),
        ", ".join(profile.skills or []) if isinstance(profile.skills, list) else str(profile.skills or ""),
    ]
    return " ".join(p for p in parts if p).strip()[:900]


def _get_embeddings(settings: Any) -> Optional[Any]:
    """Embedding provider for prefilter pass A. The stub provider produces
    hash-noise vectors whose cosine would randomly discard real listings —
    only a real provider is allowed to make discard decisions."""
    if settings.embedding.provider == "stub":
        return None
    try:
        from shared.embedding import get_embedding_provider

        return get_embedding_provider()
    except Exception as exc:
        log.warning("embedding provider unavailable — prefilter pass A disabled: %s", exc)
        return None


def _write_raw(storage_dir: Path, source: str, source_key: str, raw_text: str) -> str:
    raw_dir = storage_dir / "raw" / source
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in source_key)[:120]
    path = raw_dir / f"{safe_key}.txt"
    path.write_text(raw_text, encoding="utf-8")
    return str(path)


async def _prefilter_and_finalize(
    db: Session,
    user_id: int,
    job_id: int,
    url: str,
    extracted: list[ExtractedListing],
    *,
    search_run: Any,
    settings: Any,
    extractor: Any,
    scorer: Any,
    parser_llm: Any,
    threshold: float,
    profile: Any,
    constraints: dict[str, Any],
    diagnostics: list[Any],
) -> None:
    """Prefilter -> dedupe -> enrich -> parse+score -> auto-create -> done.
    Shared by the normal (scrape-finished) completion path AND by
    finalize_pipeline_url (the "Stop and show results" action) — both cases
    ultimately have "some already-extracted listings, no more pagination
    coming" and must turn them into real, saved results the same way."""

    listings_found = len(extracted)
    kept, dropped = await prefilter_batch(
        extractor,
        constraints,
        extracted,
        profile_digest=_profile_digest(profile),
        embeddings=_get_embeddings(settings),
    )
    if dropped:
        log.info(
            "run_pipeline_url: prefilter dropped %d/%d listing(s): %s",
            len(dropped), listings_found,
            [f"{d['listing']!r} ({d['reason']})" for d in dropped],
        )
    log.info("run_pipeline_url: %d/%d listing(s) kept after prefilter", len(kept), listings_found)
    jobs_repo.update_progress(
        db,
        job_id,
        20,
        meta={
            "url": url,
            "listings_found": listings_found,
            "listings_kept_by_prefilter": len(kept),
            "needs_continue_prompt": False,
            "scrape_diagnostics": diagnostics,
            "dropped_by_prefilter": [f"{d['listing']} — {d['reason']}" for d in dropped],
        },
    )

    if not kept:
        # Fail loudly, not silently: say WHY the run produced nothing so
        # the user can act (JS shell? tiny page? everything prefiltered?).
        if listings_found == 0:
            reason = "the scraper extracted no listings from the page"
            hints = [
                f"page {d.get('page')}: {d.get('text_chars', 0)} chars of text via "
                f"{d.get('rendering')}" + (f" (error: {d['error']})" if d.get("error") else "")
                for d in diagnostics
            ]
            if hints:
                reason += " — " + "; ".join(hints)
        else:
            reason = (
                f"all {listings_found} extracted listing(s) were dropped by the "
                "profile prefilter — relax your onboarding constraints or check the drop reasons"
            )
        log.warning("run_pipeline_url: 0 listings kept for %s: %s", url, reason)
        jobs_repo.update_progress(db, job_id, 99, meta={"empty_reason": reason})
        jobs_repo.mark_done(db, job_id, result_ref=f"listings=0 url={url} reason={reason[:400]}")
        if search_run is not None:
            search_runs_repo.update(db, search_run.id, user_id, status="done")
        return

    # ---- DEDUPE before spending on enrichment (AGENT.md §3.5): a dupe
    # caught here costs string comparisons; one that reaches the enricher
    # costs a page fetch + a strong-model call.
    kept, dupes = dedupe_listings(db, user_id, kept)
    if dupes:
        jobs_repo.update_progress(db, job_id, 20, meta={"duplicates_skipped": len(dupes)})
    if not kept:
        jobs_repo.mark_done(
            db, job_id,
            result_ref=f"listings=0 url={url} reason=all {len(dupes)} kept listing(s) were already in your library",
        )
        if search_run is not None:
            search_runs_repo.update(db, search_run.id, user_id, status="done")
        return

    # ---- ENRICH each surviving listing from its OWN dedicated page.
    # The list page crams every listing's text into one LLM call, which
    # is where fields get conflated/dropped between listings — only
    # ever hitting the network + LLM again for listings that already
    # passed the hard-constraint prefilter (never wasted on rejects).
    log.info("run_pipeline_url: fetching detail pages for %d listing(s) that passed prefilter", len(kept))
    kept = await enrich_listings(
        kept,
        extractor,
        user_agent=settings.scraper_user_agent,
        playwright_enabled=settings.playwright_enabled,
        source_url=url,
    )

    raws = [_extracted_to_raw(e, url) for e in kept]

    # ---- PARSE + SCORE in batches of BATCH_SIZE
    batch_size = max(1, settings.batch_size)
    total = len(raws)
    scored: list[tuple[Listing, float]] = []

    for batch_start in range(0, total, batch_size):
        batch = raws[batch_start : batch_start + batch_size]
        for raw in batch:
            raw_path = _write_raw(settings.storage_dir, raw.source, raw.source_key, raw.raw_text)
            listing = upsert_listing(db, user_id, raw, raw_path=raw_path)
            # async variants keep the blocking LLM calls off the event
            # loop (Session writes stay on this thread).
            await parse_listing_async(db, parser_llm, listing, raw.raw_text)
            score_row = await score_listing_async(
                db,
                scorer,
                user_id=user_id,
                profile=profile,
                listing=listing,
            )
            scored.append((listing, score_row.score))
        db.commit()
        # 20% reserved for ingest, 70% for parse+score loop, 10% for the
        # auto-create tail.
        done_pct = 20 + int(70 * (batch_start + len(batch)) / total)
        matched_so_far = sum(1 for _, s in scored if s >= threshold)
        jobs_repo.update_progress(
            db,
            job_id,
            done_pct,
            meta={
                "currently_checking": batch[-1].source_key,
                "listings_matched": matched_so_far,
            },
        )

    # ---- AUTO-CREATE applications
    log.info(
        "run_pipeline_url: threshold=%.0f — scores: %s",
        threshold, [(listing.title, score) for listing, score in scored],
    )
    auto_created = 0
    for listing, score in scored:
        if score >= threshold and app_repo.get_by_listing(db, user_id, listing.id) is None:
            app_service.create_application(
                db, user_id=user_id, listing_id=listing.id, initial_status=sm.SAVED
            )
            auto_created += 1

    jobs_repo.mark_done(
        db,
        job_id,
        result_ref=f"listings={total} auto_created={auto_created} url={url}",
    )
    if search_run is not None:
        search_runs_repo.update(
            db, search_run.id, user_id, status="done", listings_matched=auto_created
        )


async def _run_async(
    user_id: int,
    job_id: int,
    url: str,
    *,
    search_run_id: Optional[int] = None,
    resume_state: Optional[dict[str, Any]] = None,
) -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    search_run = None
    try:
        jobs_repo.mark_running(db, job_id)

        search_run = (
            search_runs_repo.get(db, search_run_id, user_id)
            if search_run_id is not None
            else search_runs_repo.create(db, user_id, url=url, job_id=job_id, status="running")
        )
        if search_run is not None:
            search_run.status = "running"
            db.commit()

        # LLM per role (factory guide §10): use the cheap "extractor" model for
        # scraping the HTML and the configured "scorer" for scoring downstream.
        extractor = get_llm(settings.llm, role="extractor")
        scorer = get_llm(settings.llm, role="scorer")
        parser_llm = get_llm(settings.llm, role="builder")

        user_settings = users_repo.get_settings(db, user_id)
        threshold = user_settings.score_threshold if user_settings else settings.default_score_threshold
        profile = users_repo.get_profile(db, user_id)
        constraints = (profile.profile_constraints if profile else None) or {}

        log.info(
            "run_pipeline_url: user_id=%s url=%s constraints=%s resuming=%s",
            user_id, url, constraints or "(none set)", resume_state is not None,
        )

        # ---- INGEST via LangGraph scraper agent (with pagination checkpoint)
        scrape_result = await run_scraper_graph(
            url,
            extractor,
            max_pages=settings.max_pages_per_url,
            user_agent=settings.scraper_user_agent,
            playwright_enabled=settings.playwright_enabled,
            pause_after_pages=PAGES_BEFORE_PAUSE,
            resume_state=resume_state,
        )
        extracted: list[ExtractedListing] = scrape_result["listings"]
        listings_found = len(extracted)
        log.info(
            "run_pipeline_url: scraper returned %d listing(s) after %d page(s), paused=%s",
            listings_found, scrape_result["pages_processed"], scrape_result["paused"],
        )

        if search_run is not None:
            search_runs_repo.update(
                db,
                search_run.id,
                user_id,
                pages_processed=scrape_result["pages_processed"],
                listings_found=listings_found,
            )

        if scrape_result["paused"]:
            # Cheap preview so the checkpoint prompt can show accurate
            # "N kept" numbers before the user decides Continue vs Stop.
            kept, dropped = await prefilter_batch(
                extractor,
                constraints,
                extracted,
                profile_digest=_profile_digest(profile),
                embeddings=_get_embeddings(settings),
            )
            if search_run is not None:
                search_run.resume_state = scrape_result["resume_state"]
                search_run.status = "awaiting_continue"
                db.commit()
            # Checkpoint gate (AGENT.md §3.8): tell the user what the pause
            # bought — found/kept/discarded — so Continue vs Stop is informed.
            # stop_reason "page_limit" means this pause is the per-run safety
            # ceiling (there's more beyond it) rather than the periodic
            # checkpoint — surfaced so the UI can word it accurately.
            jobs_repo.mark_awaiting_continue(
                db,
                job_id,
                meta={
                    "needs_continue_prompt": True,
                    "listings_matched": 0,
                    "pause_reason": scrape_result.get("stop_reason"),
                    "scrape_diagnostics": scrape_result.get("diagnostics", []),
                    "checkpoint": {
                        "pages": scrape_result["pages_processed"],
                        "found": listings_found,
                        "kept": len(kept),
                        "discarded": len(dropped),
                    },
                },
            )
            return

        await _prefilter_and_finalize(
            db, user_id, job_id, url, extracted,
            search_run=search_run,
            settings=settings,
            extractor=extractor,
            scorer=scorer,
            parser_llm=parser_llm,
            threshold=threshold,
            profile=profile,
            constraints=constraints,
            diagnostics=scrape_result.get("diagnostics", []),
        )
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
        run_id = search_run.id if search_run is not None else search_run_id
        if run_id is not None:
            search_runs_repo.update(db, run_id, user_id, status="failed")
    finally:
        db.close()


async def _finalize_now_async(
    user_id: int, job_id: int, url: str, search_run_id: int, resume_state: dict[str, Any]
) -> None:
    """"Stop and show results" while awaiting_continue: skip further
    pagination entirely and run everything extracted SO FAR through the
    rest of the pipeline. The old behavior here just flipped the search
    run's status to "cancelled" and threw away every listing already
    found and kept by the prefilter — nothing was ever written to the
    database, so the "results" the checkpoint had just shown vanished."""

    settings = get_settings()
    db: Session = SessionLocal()
    search_run = None
    try:
        jobs_repo.mark_running(db, job_id)
        search_run = search_runs_repo.get(db, search_run_id, user_id)
        if search_run is not None:
            search_run.status = "running"
            db.commit()

        extractor = get_llm(settings.llm, role="extractor")
        scorer = get_llm(settings.llm, role="scorer")
        parser_llm = get_llm(settings.llm, role="builder")

        user_settings = users_repo.get_settings(db, user_id)
        threshold = user_settings.score_threshold if user_settings else settings.default_score_threshold
        profile = users_repo.get_profile(db, user_id)
        constraints = (profile.profile_constraints if profile else None) or {}

        extracted = [ExtractedListing(**d) for d in resume_state.get("all_listings", [])]
        log.info(
            "finalize_pipeline_url: user_id=%s url=%s finalizing %d already-extracted listing(s) without further pagination",
            user_id, url, len(extracted),
        )

        await _prefilter_and_finalize(
            db, user_id, job_id, url, extracted,
            search_run=search_run,
            settings=settings,
            extractor=extractor,
            scorer=scorer,
            parser_llm=parser_llm,
            threshold=threshold,
            profile=profile,
            constraints=constraints,
            diagnostics=[],
        )
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
        run_id = search_run.id if search_run is not None else search_run_id
        if run_id is not None:
            search_runs_repo.update(db, run_id, user_id, status="failed")
    finally:
        db.close()


def _run(coro) -> None:
    try:
        asyncio.run(coro)
    except RuntimeError:
        # If an event loop is already running (e.g. arq worker), fall back.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()


def run_pipeline_url(user_id: int, job_id: int, url: str, *, search_run_id: Optional[int] = None) -> None:
    """Sync entry used by FastAPI BackgroundTasks. Wraps the async runner."""

    _run(_run_async(user_id, job_id, url, search_run_id=search_run_id))


def continue_pipeline_url(
    user_id: int, job_id: int, url: str, search_run_id: int, resume_state: dict[str, Any]
) -> None:
    """Resume a paused (awaiting_continue) run from its serialized state."""

    _run(_run_async(user_id, job_id, url, search_run_id=search_run_id, resume_state=resume_state))


def finalize_pipeline_url(
    user_id: int, job_id: int, url: str, search_run_id: int, resume_state: dict[str, Any]
) -> None:
    """"Stop and show results" — sync entry used by FastAPI BackgroundTasks.
    Skips further pagination and processes what's already been extracted."""

    _run(_finalize_now_async(user_id, job_id, url, search_run_id, resume_state))


# Back-compat: the old fixture-driven entry point, still reachable via the
# legacy POST /api/runs endpoint. Keeps Phase-1 verifiability without the
# scraper agent.
def run_pipeline(user_id: int, job_id: int) -> None:
    from worker.pipeline.ingest.fixture import FixtureScraper

    settings = get_settings()
    db: Session = SessionLocal()
    try:
        jobs_repo.mark_running(db, job_id)
        llm = get_llm(settings.llm, role="builder")
        scorer = get_llm(settings.llm, role="scorer")
        profile = users_repo.get_profile(db, user_id)
        user_settings = users_repo.get_settings(db, user_id)
        threshold = user_settings.score_threshold if user_settings else settings.default_score_threshold

        raws = list(FixtureScraper().fetch())
        total = max(1, len(raws))
        scored: list[tuple[Listing, float]] = []
        for index, raw in enumerate(raws, start=1):
            raw_path = _write_raw(settings.storage_dir, raw.source, raw.source_key, raw.raw_text)
            listing = upsert_listing(db, user_id, raw, raw_path=raw_path)
            parse_listing(db, llm, listing, raw.raw_text)
            score_row = score_listing(
                db, scorer, user_id=user_id, profile=profile, listing=listing,
            )
            scored.append((listing, score_row.score))
            db.commit()
            jobs_repo.update_progress(db, job_id, int(index * 90 / total))

        auto = 0
        for listing, score in scored:
            if score >= threshold and app_repo.get_by_listing(db, user_id, listing.id) is None:
                app_service.create_application(
                    db, user_id=user_id, listing_id=listing.id, initial_status=sm.SAVED
                )
                auto += 1

        jobs_repo.mark_done(db, job_id, result_ref=f"listings={len(raws)} auto_created={auto}")
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
    finally:
        db.close()
