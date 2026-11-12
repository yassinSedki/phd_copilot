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
        shell lint test clean docker-up docker-down \
        kind-up kind-down kind-load k8s-secret helm-dev helm-lint

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
	@echo "  make kind-up               local k8s cluster + ingress-nginx + metrics-server + dev Postgres"
	@echo "  make k8s-secret            create/update the phd-secrets Secret from .env.k8s"
	@echo "  make helm-dev              build, load into kind, helm upgrade --install (tag = git SHA)"
	@echo "  make helm-lint             lint + render the chart"
	@echo "  make kind-down             delete the local cluster"
	@echo ""

install:
	$(POETRY) install

dev: backend

# WATCHFILES_FORCE_POLLING: inotify events never reach WSL for files on
# /mnt/* (Windows-mounted drives), so the watcher must poll or edits made
# from Windows never trigger a reload. Harmless on native filesystems.
backend:
	WATCHFILES_FORCE_POLLING=true $(POETRY) run uvicorn app.main:app \
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

# ---- Kubernetes (local kind cluster) -----------------------------------------
# Images are tagged with the git commit, never a reused tag like "dev": an
# unchanged tag means an unchanged pod spec, so Kubernetes would keep running
# the old image. Commit, then `make helm-dev`.
TAG   ?= $(shell git rev-parse --short HEAD)
NS    ?= phd-dev
CHART := deploy/helm/phd-copilot

kind-up:
	kind create cluster --config deploy/kind/cluster.yaml
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
	kubectl -n kube-system patch deployment metrics-server --type=json \
		-p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
	kubectl -n ingress-nginx wait --for=condition=ready pod \
		--selector=app.kubernetes.io/component=controller --timeout=180s
	kubectl create namespace $(NS)
	kubectl -n $(NS) apply -f deploy/kind/postgres.yaml
	kubectl -n $(NS) rollout status deploy/postgres --timeout=180s

kind-down:
	kind delete cluster --name phd

kind-load:
	docker build -f backend/Dockerfile -t phd-backend:$(TAG) .
	docker build -t phd-frontend:$(TAG) frontend
	kind load docker-image phd-backend:$(TAG) phd-frontend:$(TAG) --name phd

k8s-secret:
	@test -f .env.k8s || (echo "Missing .env.k8s — copy .env.k8s.example and fill it in"; exit 1)
	kubectl -n $(NS) create secret generic phd-secrets --from-env-file=.env.k8s \
		--dry-run=client -o yaml | kubectl apply -f -

helm-lint:
	helm lint $(CHART) -f $(CHART)/values-dev.yaml
	helm template phd $(CHART) -f $(CHART)/values-dev.yaml > /dev/null

helm-dev: kind-load
	helm upgrade --install phd $(CHART) -n $(NS) \
		-f $(CHART)/values-dev.yaml \
		--set image.backend.tag=$(TAG) --set image.frontend.tag=$(TAG) \
		--atomic --wait --timeout 5m
