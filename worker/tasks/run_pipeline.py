"""run_pipeline_url: scrape ANY URL → parse → score → auto-create apps.

Architecture: phd copilot.md → scraper-agent diagram + "Batch processing
with live progress". Listings are processed in batches of BATCH_SIZE
(default 5) and `jobs.progress` is updated after each batch so the UI
gets near-live feedback.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.database import SessionLocal
from shared.models import Listing
from shared.models.base import utcnow
from shared.repositories import applications as app_repo
from shared.repositories import jobs as jobs_repo
from shared.repositories import users as users_repo
from shared.services import applications as app_service
from shared.services import state_machine as sm
from worker.pipeline.ingest import run_scraper_graph
from worker.pipeline.ingest.base import RawListing
from shared.llm import ExtractedListing, get_llm
from worker.pipeline.parse.parser import parse_listing, upsert_listing
from worker.pipeline.score.scorer import score_listing


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
            "required_docs": "",
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


def _write_raw(storage_dir: Path, source: str, source_key: str, raw_text: str) -> str:
    raw_dir = storage_dir / "raw" / source
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in source_key)[:120]
    path = raw_dir / f"{safe_key}.txt"
    path.write_text(raw_text, encoding="utf-8")
    return str(path)


async def _run_async(user_id: int, job_id: int, url: str) -> None:
    settings = get_settings()
    db: Session = SessionLocal()
    try:
        jobs_repo.mark_running(db, job_id)

        # LLM per role (factory guide §10): use the cheap "extractor" model for
        # scraping the HTML and the configured "scorer"/"scorer_strong" for
        # scoring downstream.
        extractor = get_llm(settings.llm, role="extractor")
        scorer = get_llm(settings.llm, role="scorer")
        scorer_strong = get_llm(settings.llm, role="scorer_strong")
        parser_llm = get_llm(settings.llm, role="builder")

        user_settings = users_repo.get_settings(db, user_id)
        threshold = user_settings.score_threshold if user_settings else settings.default_score_threshold
        low_threshold = settings.low_score_threshold
        profile = users_repo.get_profile(db, user_id)

        # ---- INGEST via LangGraph scraper agent
        extracted: list[ExtractedListing] = await run_scraper_graph(
            url,
            extractor,
            max_pages=settings.max_pages_per_url,
            user_agent=settings.scraper_user_agent,
            playwright_enabled=settings.playwright_enabled,
        )
        if not extracted:
            jobs_repo.mark_done(db, job_id, result_ref=f"listings=0 url={url}")
            return

        jobs_repo.update_progress(db, job_id, 20)
        raws = [_extracted_to_raw(e, url) for e in extracted]

        # ---- PARSE + SCORE in batches of BATCH_SIZE
        batch_size = max(1, settings.batch_size)
        total = len(raws)
        scored: list[tuple[Listing, float]] = []

        for batch_start in range(0, total, batch_size):
            batch = raws[batch_start : batch_start + batch_size]
            for raw in batch:
                raw_path = _write_raw(settings.storage_dir, raw.source, raw.source_key, raw.raw_text)
                listing = upsert_listing(db, user_id, raw, raw_path=raw_path)
                parse_listing(db, parser_llm, listing, raw.raw_text)
                score_row = score_listing(
                    db,
                    scorer,
                    user_id=user_id,
                    profile=profile,
                    listing=listing,
                    strong_llm=scorer_strong,
                )
                scored.append((listing, score_row.score))
            db.commit()
            # 20% reserved for ingest, 70% for parse+score loop, 10% for the
            # auto-create + expire tail.
            done_pct = 20 + int(70 * (batch_start + len(batch)) / total)
            jobs_repo.update_progress(db, job_id, done_pct)

        # ---- AUTO-CREATE applications
        auto_created = 0
        for listing, score in scored:
            if score >= threshold and app_repo.get_by_listing(db, user_id, listing.id) is None:
                app_service.create_application(
                    db, user_id=user_id, listing_id=listing.id, initial_status=sm.REVIEWING
                )
                auto_created += 1
            elif score < low_threshold:
                continue

        app_service.expire_overdue(db, user_id)
        jobs_repo.mark_done(
            db,
            job_id,
            result_ref=f"listings={total} auto_created={auto_created} url={url}",
        )
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
    finally:
        db.close()


def run_pipeline_url(user_id: int, job_id: int, url: str) -> None:
    """Sync entry used by FastAPI BackgroundTasks. Wraps the async runner."""

    try:
        asyncio.run(_run_async(user_id, job_id, url))
    except RuntimeError:
        # If an event loop is already running (e.g. arq worker), fall back.
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run_async(user_id, job_id, url))
        finally:
            loop.close()


# Back-compat: the old fixture-driven entry point. Used by the daily-run
# scheduler today. Keeps Phase-1 verifiability without the scraper agent.
def run_pipeline(user_id: int, job_id: int) -> None:
    from worker.pipeline.ingest.fixture import FixtureScraper

    settings = get_settings()
    db: Session = SessionLocal()
    try:
        jobs_repo.mark_running(db, job_id)
        llm = get_llm(settings.llm, role="builder")
        scorer = get_llm(settings.llm, role="scorer")
        scorer_strong = get_llm(settings.llm, role="scorer_strong")
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
                strong_llm=scorer_strong,
            )
            scored.append((listing, score_row.score))
            db.commit()
            jobs_repo.update_progress(db, job_id, int(index * 90 / total))

        auto = 0
        for listing, score in scored:
            if score >= threshold and app_repo.get_by_listing(db, user_id, listing.id) is None:
                app_service.create_application(
                    db, user_id=user_id, listing_id=listing.id, initial_status=sm.REVIEWING
                )
                auto += 1

        app_service.expire_overdue(db, user_id)
        jobs_repo.mark_done(db, job_id, result_ref=f"listings={len(raws)} auto_created={auto}")
    except Exception as exc:
        db.rollback()
        jobs_repo.mark_failed(db, job_id, error=f"{exc}\n{traceback.format_exc()}")
    finally:
        db.close()
