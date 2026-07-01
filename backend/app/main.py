from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from shared.database import engine
from shared.models import Base
from app.routers import applications, auth, dashboard, deepdive, jobs, listings, profile, runs
from app.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1 prototype: create tables on startup. Swap for Alembic when
    # moving off SQLite (architecture section 13, Phase 1 / 14).
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="phd-copilot",
        version="0.1.0",
        description=(
            "Phase 1 backend MVP. See architecture/phd_copilot_architecture.txt. "
            "Pipeline runs in-process via BackgroundTasks; ingest+LLM are stubbed."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(runs.router)
    app.include_router(jobs.router)
    app.include_router(listings.router)
    app.include_router(applications.router)
    app.include_router(deepdive.router)
    app.include_router(dashboard.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "llm_provider": settings.llm_provider,
            "ingest_source": settings.ingest_source,
        }

    return app


app = create_app()
