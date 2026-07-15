from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from shared.database import get_db
from shared.models import User
from shared.repositories import jobs as jobs_repo
from shared.repositories import search_runs as search_runs_repo
from app.schemas.job import JobRead, RunResponse

router = APIRouter(prefix="/api", tags=["runs"])


class RunUrlRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


@router.post("/runs/url", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_run_url(
    body: RunUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    """Universal URL pipeline. Hand any PhD/job listing URL — the scraper
    agent (LangGraph) fetches it (with Playwright fallback), extracts
    listings, pre-filters against the user's hard constraints, parses and
    scores them in batches of BATCH_SIZE. Pauses for a "continue?" prompt
    every few pages (see /api/search-runs/:id/continue)."""

    if not body.url.lower().startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="url must start with http(s)://")

    job = jobs_repo.create(db, current_user.id, job_type="run_pipeline_url")
    search_run = search_runs_repo.create(db, current_user.id, url=body.url, job_id=job.id, status="queued")
    from worker.tasks.run_pipeline import run_pipeline_url

    background_tasks.add_task(run_pipeline_url, current_user.id, job.id, body.url, search_run_id=search_run.id)
    return RunResponse(job_id=job.id, search_run_id=search_run.id)


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
def start_run_legacy(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    """Legacy fixture-driven pipeline (no URL). Kept for the daily-run
    scheduler and tests. New clients should call /runs/url."""

    job = jobs_repo.create(db, current_user.id, job_type="run_pipeline")
    from worker.tasks.run_pipeline import run_pipeline

    background_tasks.add_task(run_pipeline, current_user.id, job.id)
    return RunResponse(job_id=job.id)


@router.get("/runs/{job_id}", response_model=JobRead)
def get_run(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRead:
    job = jobs_repo.get(db, current_user.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return JobRead.model_validate(job)
