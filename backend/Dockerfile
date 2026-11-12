# Backend image — HTTP tier + in-process pipeline.
# Ships backend.app + shared + worker + Alembic migrations.
#
# worker/ is included because the API still runs the pipeline in-process
# (routers lazily `from worker.tasks...` inside BackgroundTasks) and reads the
# drafting templates from worker/pipeline/draft/templates/. Drop it from this
# image once the arq + Redis worker split lands. Playwright is NOT installed
# here: it is imported lazily, so JS-rendered pages just skip the browser
# fallback (worker/Dockerfile has the Chromium build).
#
# Same image runs two ways:
#   uvicorn (default CMD)          → the API
#   alembic upgrade head           → the migration Job / compose `migrate` step

# ---------- builder: resolve and install dependencies into an isolated venv
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# requirements.txt alone first: this layer stays cached until dependencies
# change, so code edits never trigger a reinstall.
COPY backend/requirements.txt /tmp/requirements.txt
# The venv's own pip/setuptools (~24 MB) are build tools: drop them so they
# never reach the runtime stage.
RUN pip install -r /tmp/requirements.txt \
 && pip uninstall -y pip setuptools wheel

# ---------- runtime: slim base + the venv, no pip cache or build leftovers
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/backend:/app \
    STORAGE_DIR=/data/storage

# Unprivileged user with a fixed UID — Kubernetes `runAsUser: 10001` matches it.
# STORAGE_DIR is pre-created and owned by that user; a named volume mounted
# there inherits this ownership on first use.
RUN useradd --create-home --uid 10001 app \
 && mkdir -p /data/storage \
 && chown app:app /data/storage

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app backend     ./backend
COPY --chown=app:app shared      ./shared
COPY --chown=app:app worker      ./worker
COPY --chown=app:app migrations  ./migrations
COPY --chown=app:app alembic.ini ./alembic.ini

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
