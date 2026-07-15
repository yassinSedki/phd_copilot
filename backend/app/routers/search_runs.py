from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.schemas.job import SearchRunRead
from shared.database import get_db
from shared.models import User
from shared.repositories import jobs as jobs_repo
from shared.repositories import search_runs as search_runs_repo

router = APIRouter(prefix="/api/search-runs", tags=["search-runs"])


@router.get("", response_model=list[SearchRunRead])
def list_search_runs(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SearchRunRead]:
    runs = search_runs_repo.list_by_user(db, current_user.id)[:limit]
    return [SearchRunRead.model_validate(r) for r in runs]


@router.get("/{search_run_id}", response_model=SearchRunRead)
def get_search_run(
    search_run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunRead:
    run = search_runs_repo.get(db, search_run_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search run not found")
    return SearchRunRead.model_validate(run)


@router.post("/{search_run_id}/continue", response_model=SearchRunRead)
def continue_search_run(
    search_run_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunRead:
    run = search_runs_repo.get(db, search_run_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search run not found")
    if run.status != "awaiting_continue" or not run.resume_state:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="search run is not paused")
    if run.job_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="search run has no associated job")

    jobs_repo.mark_running(db, run.job_id)
    run.status = "running"
    db.commit()

    from worker.tasks.run_pipeline import continue_pipeline_url

    background_tasks.add_task(
        continue_pipeline_url, current_user.id, run.job_id, run.url, run.id, run.resume_state
    )
    return SearchRunRead.model_validate(run)


@router.post("/{search_run_id}/cancel", response_model=SearchRunRead)
def cancel_search_run(
    search_run_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchRunRead:
    run = search_runs_repo.get(db, search_run_id, current_user.id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="search run not found")
    if run.status in {"done", "cancelled", "failed"}:
        return SearchRunRead.model_validate(run)

    # "Stop and show results" at a checkpoint: the run has already found and
    # kept listings (resume_state carries them) — finalize them instead of
    # discarding, so the numbers the user just saw actually get saved.
    if run.status == "awaiting_continue" and run.resume_state and run.job_id is not None:
        jobs_repo.mark_running(db, run.job_id)
        run.status = "running"
        db.commit()

        from worker.tasks.run_pipeline import finalize_pipeline_url

        background_tasks.add_task(
            finalize_pipeline_url, current_user.id, run.job_id, run.url, run.id, run.resume_state
        )
        return SearchRunRead.model_validate(run)

    run.status = "cancelled"
    run.resume_state = None
    db.commit()
    if run.job_id is not None:
        jobs_repo.mark_cancelled(db, run.job_id)
    return SearchRunRead.model_validate(run)
