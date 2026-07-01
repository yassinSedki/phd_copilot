"""Daily run scheduling (architecture sections 11 / 14).

Phase 5 simplification: APScheduler embedded in the API process. When the
real worker process exists (arq + Redis), move this to the worker side and
make the API stateless.

Set DAILY_RUN=off in .env to disable (default off, until you've wired a real
scraper — running the daily pipeline against fixture data isn't useful).
"""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.database import SessionLocal
from shared.models import User
from shared.repositories import jobs as jobs_repo

log = logging.getLogger("phd_copilot.scheduler")
_scheduler: BackgroundScheduler | None = None


def _daily_run_all_users() -> None:
    from worker.tasks.run_pipeline import run_pipeline

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            job = jobs_repo.create(db, user.id, job_type="daily_run")
            log.info("scheduling daily_run user_id=%s job_id=%s", user.id, job.id)
            try:
                run_pipeline(user.id, job.id)
            except Exception:
                log.exception("daily_run failed for user_id=%s", user.id)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    if os.environ.get("DAILY_RUN", "off").lower() != "on":
        log.info("daily_run disabled (set DAILY_RUN=on to enable)")
        return

    get_settings()  # validate config
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _daily_run_all_users,
        trigger="cron",
        hour=int(os.environ.get("DAILY_RUN_HOUR", "6")),
        minute=int(os.environ.get("DAILY_RUN_MINUTE", "0")),
        id="daily_run",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("scheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
