from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.models import Job
from shared.models.base import utcnow


def create(db: Session, user_id: int, job_type: str) -> Job:
    job = Job(user_id=user_id, type=job_type, status="queued", progress=0)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get(db: Session, user_id: int, job_id: int) -> Optional[Job]:
    return db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user_id))


def mark_running(db: Session, job_id: int) -> None:
    job = db.get(Job, job_id)
    if job:
        job.status = "running"
        db.commit()


def update_progress(db: Session, job_id: int, progress: int) -> None:
    job = db.get(Job, job_id)
    if job:
        job.progress = progress
        db.commit()


def mark_done(db: Session, job_id: int, result_ref: Optional[str] = None) -> None:
    job = db.get(Job, job_id)
    if job:
        job.status = "done"
        job.progress = 100
        job.result_ref = result_ref
        job.finished_at = utcnow()
        db.commit()


def mark_failed(db: Session, job_id: int, error: str) -> None:
    job = db.get(Job, job_id)
    if job:
        job.status = "failed"
        job.error = error
        job.finished_at = utcnow()
        db.commit()
