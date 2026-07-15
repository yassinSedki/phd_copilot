import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import get_settings
from app.routers import (
    applications,
    auth,
    dashboard,
    deepdive,
    documents,
    jobs,
    listings,
    onboarding,
    profile,
    referees,
    reference_requests,
    runs,
    search_runs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is Alembic's job now (migrations/versions/) — no more
    # create_all-on-boot. That shortcut silently created tables outside
    # Alembic's tracking and started colliding with real migrations once
    # they existed.
    yield


def create_app() -> FastAPI:
    # The app never configured a log level, so every `logging.getLogger(...)`
    # call site in shared/worker (scraper agent, LLM fallback warnings,
    # pipeline stage summaries) was silently invisible — only uvicorn's own
    # access-log lines showed up. This makes `phd_copilot.*` loggers print at
    # INFO to stdout; override with LOG_LEVEL=DEBUG/WARNING in .env if noisy.
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )

    settings = get_settings()

    # Refuse to serve auth with a forgeable signing key. The default value
    # is public knowledge; anyone could mint valid tokens with it.
    if settings.jwt_secret == "change-me-in-production" or len(settings.jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is unset, default, or too short (<32 chars). "
            "Set a strong random JWT_SECRET in .env before starting the API."
        )

    app = FastAPI(
        title="phd-copilot",
        version="0.1.0",
        description=(
            "PhD Copilot backend. See architecture/phd_copilot_architecture.txt. "
            "Pipeline runs in-process via BackgroundTasks; LLM provider is configured via LLM__PROVIDER."
        ),
        lifespan=lifespan,
    )

    # Explicit origins: a wildcard combined with allow_credentials is both
    # insecure and rejected by browsers.
    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    if settings.frontend_base_url:
        cors_origins.append(settings.frontend_base_url.rstrip("/"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(onboarding.router)
    app.include_router(profile.router)
    app.include_router(runs.router)
    app.include_router(jobs.router)
    app.include_router(listings.router)
    app.include_router(applications.router)
    app.include_router(documents.router)
    app.include_router(deepdive.router)
    app.include_router(dashboard.router)
    app.include_router(search_runs.router)
    app.include_router(referees.router)
    app.include_router(reference_requests.router)

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {
            "status": "ok",
            "llm_provider": settings.llm.provider,
        }

    return app


app = create_app()
