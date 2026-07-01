# phd-copilot

Agentic PhD/scholarship hunting platform. Paste any listing URL, upload your CV, get ranked matches with conversational cover letters.

See [`architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md) for the structural overview and [`HOW_IT_WORKS.md`](./HOW_IT_WORKS.md) for the implementation walkthrough.

---

## Quick start

You need: **Python 3.11+**, **Poetry 1.8+**, **Node 18+** (frontend), **make** (already on macOS/Linux/WSL; on Windows install via Chocolatey or use WSL). Database is a hosted Postgres URL in `.env` — no Docker required.

```bash
make install                         # poetry install
cp .env.example .env
# edit .env: set COHERE_API_KEY (or ANTHROPIC), DATABASE_URL, JWT_SECRET

make migrate-new MSG="initial schema"   # one-time, generates the first migration
make migrate                            # applies it to your Postgres

make backend                            # FastAPI on :8000, /docs is Swagger
```

In a second terminal:

```bash
make front                              # Vite on :5173, proxies /api → :8000
```

Open http://localhost:5173. `make help` lists every task.

---

## Database

PostgreSQL is the supported runtime. The default `DATABASE_URL` in [`.env.example`](./.env.example) points at the compose-managed Postgres on `localhost:5432`. To use a host-installed Postgres or a managed instance, edit the URL.

### Migrations

Alembic is the source of truth for schema changes:

```bash
# After editing any model in shared/models/
poetry run alembic revision --autogenerate -m "describe the change"

# Apply pending migrations
poetry run alembic upgrade head

# Look at history
poetry run alembic history
```

`migrations/env.py` reads `DATABASE_URL` from `shared.config.get_settings()` so there's no second source of truth. The `versions/` folder is committed to the repo.

### SQLite (tests only)

SQLite still works for ad-hoc tests via `DATABASE_URL=sqlite:///./local.db`, but it isn't a supported production runtime — the JSON columns behave differently and some Postgres-specific features (concurrent index builds, partial indexes, etc.) aren't available.

---

## Production-shaped (everything in Docker)

```bash
docker compose up --build
# backend  → http://localhost:8000
# frontend → http://localhost:5173
# postgres → :5432
# redis    → :6379
```

The worker container is declared but gated behind `--profile worker` (the BackgroundTasks path in the backend still drives the pipeline for now). Once the arq entry point lands, `docker compose --profile worker up` brings it online.

---

## Provider switch (offline ↔ real Claude)

The whole codebase runs without an API key. To turn on Claude:

```env
LLM__PROVIDER=anthropic
LLM__API_KEY=sk-ant-...
```

Per-role overrides:

```env
LLM__ROLE_MODELS__SCORER=claude-haiku-4-5-20251001
LLM__TEMPERATURE_REFINER=0.4
```

See [`architecture/ARCHITECTURE.md` §5](../architecture/ARCHITECTURE.md) for the full role/model/temperature table.

---

## Layout

```
phd-copilot/
  pyproject.toml           ← Poetry-managed deps
  alembic.ini              ← migration config
  migrations/              ← Alembic env + versions
  docker-compose.yml
  .env.example
  run.py                   ← dev launcher (PYTHONPATH + uvicorn)

  shared/                  ← contracts depended on by both other packages
    config.py database.py models/ repositories/ services/ llm/ cv/

  backend/                 ← HTTP tier (lean image, no Playwright)
    Dockerfile
    app/  main.py auth/ routers/ schemas/ services/cover_letters.py

  worker/                  ← slow-work tier (Playwright + LangGraph image)
    Dockerfile
    pipeline/  ingest/ parse/ score/ draft/ deepdive/
    tasks/     run_pipeline.py deep_dive.py

  frontend/                ← Vite + React + TS + Tailwind SPA
```

Import direction is one-way: `backend` and `worker` never import each other; both import from `shared`. See [`architecture/ARCHITECTURE.md` §2](../architecture/ARCHITECTURE.md).

---

## Useful commands

Everything goes through `make`. Run `make help` for the menu.

```bash
make install                       # poetry install
make backend                       # dev backend (FastAPI on :8000)
make front                         # dev frontend (Vite on :5173)
make migrate                       # alembic upgrade head
make migrate-new MSG="add X col"   # autogenerate a new migration
make db-reset                      # downgrade to base then upgrade (DESTRUCTIVE)
make shell                         # spawn a shell inside the Poetry venv
make lint                          # ruff check
make test                          # pytest
make clean                         # remove caches + local storage
make docker-up                     # docker compose up --build
make docker-down                   # docker compose down
```

If you don't have `make` on Windows: install via Chocolatey (`choco install make`), or run the underlying `poetry run uvicorn app.main:app --reload` and `poetry run alembic ...` commands directly.
