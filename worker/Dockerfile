# Worker image — slow-work tier.
# Imports: worker + shared. Does NOT include backend/ — the worker has no
# HTTP surface; it consumes jobs (today: via the same process; tomorrow:
# via arq + Redis) and writes results back to the DB.
#
# Heavier than the backend image because it ships Playwright + Chromium for
# JS-rendered scrape fallback. Keeping it separate keeps the API image lean.

FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Worker reuses the backend requirements set for now (langchain, langgraph,
# sqlalchemy, etc.). When backend gets a separate, leaner requirements file,
# split this too.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt playwright==1.49.1

COPY worker /app/worker
COPY shared /app/shared

# Default command for an arq-based worker (placeholder — wire when arq is
# adopted). For now, the worker functions are called by the backend process
# via BackgroundTasks and this image is unused.
CMD ["python", "-c", "print('worker image ready; arq entry point goes here')"]
