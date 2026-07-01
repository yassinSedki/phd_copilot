# phd-copilot dev tasks. Run `make` (or `make help`) for the menu.
#
# Backend lives under backend/, shared lives at the repo root, worker lives
# at the repo root. `poetry install` editable-installs all three via the
# `packages = [...]` directive in pyproject.toml, so `uvicorn app.main:app`
# finds them with no sys.path hacks.

POETRY ?= poetry
HOST   ?= 127.0.0.1
PORT   ?= 8000

.DEFAULT_GOAL := help
.PHONY: help install dev backend front migrate migrate-new db-reset \
        shell lint test clean docker-up docker-down

help:
	@echo ""
	@echo "phd-copilot — dev tasks"
	@echo ""
	@echo "  make install               poetry install (creates venv, installs deps)"
	@echo "  make dev                   alias for: make backend"
	@echo "  make backend               start FastAPI on $(HOST):$(PORT) with --reload"
	@echo "  make front                 start the Vite frontend on :5173"
	@echo ""
	@echo "  make migrate               apply pending Alembic migrations"
	@echo "  make migrate-new MSG='...' autogenerate a new migration from models"
	@echo "  make db-reset              downgrade to base then upgrade head (DESTRUCTIVE)"
	@echo ""
	@echo "  make shell                 spawn a shell inside the Poetry venv"
	@echo "  make lint                  ruff check"
	@echo "  make test                  pytest"
	@echo "  make clean                 remove caches + local storage"
	@echo ""
	@echo "  make docker-up             docker compose up --build"
	@echo "  make docker-down           docker compose down"
	@echo ""

install:
	$(POETRY) install

dev: backend

backend:
	$(POETRY) run uvicorn app.main:app \
		--host $(HOST) --port $(PORT) \
		--reload --reload-dir backend --reload-dir worker --reload-dir shared

front:
	cd frontend && npm install && npm run dev

migrate:
	$(POETRY) run alembic upgrade head

migrate-new:
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make migrate-new MSG='describe the change'"; \
		exit 1; \
	fi
	$(POETRY) run alembic revision --autogenerate -m "$(MSG)"

db-reset:
	$(POETRY) run alembic downgrade base
	$(POETRY) run alembic upgrade head

shell:
	$(POETRY) shell

lint:
	$(POETRY) run ruff check .

test:
	$(POETRY) run pytest

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache storage smoketest.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

docker-up:
	docker compose up --build

docker-down:
	docker compose down
