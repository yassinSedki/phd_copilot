# How phd-copilot works — v0.2

A walkthrough of what's in this repo, how the pieces fit, and what happens when you click a button. Pairs with the two spec files:

- [phd copilot.md](../phd%20copilot.md) — the product/architecture spec.
- [ingest_and_llm_factory_guide.md](../ingest_and_llm_factory_guide.md) — the patterns that drive the LLM / ingest layer.

> **Roadmap Phases 01–13** (`architecture/roadmap/`) shipped since this walkthrough was written — see
> `architecture/roadmap/NOTES.md` for the authoritative list of what changed. Highlights: Kanban → tables (tracker +
> opportunities), single-tier scoring + constraint pre-filter (no more cheap-then-strong rescorer), generic
> `documents` model → `document_versions`, Google OAuth + CV onboarding, reference-letter requests, deep-research
> refresh. Any walkthrough step below describing those old behaviors is superseded.

---

## 1. The shape

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser ── React SPA (Vite, Tailwind, TanStack Query, Zustand)      │
└─────────────────────────────┬────────────────────────────────────────┘
                              │ HTTPS (REST/JSON)
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI ── routers → services → repositories → SQLAlchemy           │
│  + BackgroundTasks (dev) | arq + Redis (production)                  │
└──────────┬──────────────────────────────────────┬────────────────────┘
           │ reads/writes                         │ writes raw + outputs
           ▼                                      ▼
       PostgreSQL (Docker-managed in dev + prod)     storage/  (CVs, raw HTML,
                                                       cover-letter MD)
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Worker pipeline + LangGraph agents                                   │
│                                                                       │
│  Scraper Agent (LangGraph)  → Parse → Score → auto-track             │
│  Cover-letter service       → Refiner (chat) → Email body            │
│  Deep-Dive Agent (LangGraph)→ Outreach draft                         │
└──────────────────────────────────────────────────────────────────────┘
```

In dev the worker runs inside the API process via `BackgroundTasks`. The `jobs` table is the source of truth for progress, so swapping in arq+Redis is a localised change — the API and the frontend don't care.

---

## 2. Repo layout (v0.2)

```
phd-copilot/
  pyproject.toml               ← Poetry (preferred)
  Makefile                     ← `make backend`, `make migrate`, `make front`, ...
  docker-compose.yml           ← backend + frontend + postgres + redis
  .env.example
  backend/
    Dockerfile
    requirements.txt           ← pip alternative
    app/
      main.py
      config.py                ← Settings + nested LLMSettings (factory guide §12)
      database.py
      scheduler.py             ← APScheduler daily_run (off by default)
      models/                  ← User/Profile/Settings/Document/Listing/Score/
                                  Application/CoverLetter/Contact/Outreach/Job
      schemas/                 ← Pydantic request/response shapes
      auth/                    ← bcrypt + JWT + FastAPI deps
      repositories/            ← all DB access
      services/                ← business logic
        state_machine.py
        applications.py
        cover_letters.py       ← generate / refine-via-chat / email body
      routers/                 ← thin HTTP layer
  worker/
    pipeline/
      llm/                     ← factory guide §9 implementation
        base.py                ← LLMClient ABC
        factory.py             ← _PROVIDER_REGISTRY + get_llm(settings, role)
        errors.py              ← LLMError + LLMErrorCode
        types.py               ← Parsed/Score/Drafted/Email/Outreach/etc
        providers/
          stub.py              ← deterministic, no SDK, no network
          anthropic.py         ← langchain-anthropic, lazy-imported
      ingest/
        scraper_graph.py       ← LangGraph universal URL scraper agent
        fixture.py             ← offline fallback for tests/CI
      parse/parser.py
      score/scorer.py          ← cheap pass + strong rescorer for borderline
      draft/templates/cover_letter.md
      deepdive/
        research_graph.py      ← LangGraph deep-dive agent
      cv/extract.py            ← pypdf + python-docx, lazy imports
    tasks/
      run_pipeline.py          ← scraper agent → parse → score, batches of 5
      deep_dive.py             ← deep-dive agent → contact + outreach
  frontend/                    ← Vite + React + TS + Tailwind + TanStack Query
```

---

## 3. The LLM factory (the spine)

Every LLM call in the codebase goes through `get_llm(settings.llm, role)`. Adding a new provider takes two edits: write `providers/<name>.py` and add one row to `_PROVIDER_REGISTRY`. Replicates the pattern from `ingest_and_llm_factory_guide.md` §9–§10.

```
worker/pipeline/llm/
  base.py        ← LLMClient ABC (invoke, ainvoke, plus app-specific helpers)
  factory.py     ← _PROVIDER_REGISTRY + get_llm(settings, role)
  errors.py      ← LLMError + LLMErrorCode (every provider translates here)
  types.py       ← dataclasses: ParsedListing, ScoreResult, ...
  providers/
    stub.py      ← deterministic fallback. No SDK, no network. Same input → same output.
    anthropic.py ← real Claude via langchain-anthropic. SDK lazy-imported in __init__.
```

**Roles, models, temperatures.** `LLMSettings.role_models` maps role names to model IDs. The factory derives temperature + `json_mode` from the role. Different pipeline steps have different reliability/cost needs:

| Role             | Default model         | Temp | json_mode | Used by                            |
| ---------------- | --------------------- | ---- | --------- | ---------------------------------- |
| `extractor`      | sonnet                | 0.0  | ✓         | Scraper agent (HTML → listings)    |
| `scorer`         | haiku                 | 0.0  | ✓         | First score pass (cheap)           |
| `scorer_strong`  | sonnet                | 0.1  | ✓         | Re-score in the borderline band    |
| `drafter`        | sonnet                | 0.3  | ✗         | Initial cover letter + email body  |
| `refiner`        | sonnet                | 0.3  | ✗         | Conversational letter refinement   |
| `researcher`     | sonnet                | 0.2  | ✓         | Deep-dive agent nodes              |
| `builder`        | sonnet                | 0.1  | ✓         | Parse step                         |

Override anything from `.env`:

```
LLM__ROLE_MODELS__SCORER=claude-haiku-4-5-20251001
LLM__TEMPERATURE_REFINER=0.4
```

The nested `LLM__` delimiter is Pydantic-Settings' way of flattening env vars onto a nested model — see [factory guide §12](../ingest_and_llm_factory_guide.md#12-configuration).

**Lazy SDK imports.** `AnthropicLLMClient.__init__` imports `langchain_anthropic` *inside the function body* — so the codebase runs fine when only `LLM__PROVIDER=stub` is used and `langchain-anthropic` is not installed.

**Error translation.** Every provider has `_translate_error()` that catches its own SDK exceptions and re-raises as `LLMError(code=...)`. Pipeline code catches one type, not one per provider.

---

## 4. The pipeline (where the value is)

### 4.1 Universal URL ingestion — LangGraph scraper agent

User pastes any listing URL. The agent at `worker/pipeline/ingest/scraper_graph.py` runs the graph from [phd copilot.md](../phd%20copilot.md#agent-1--universal-scraper-agent):

```
fetch_simple ──► [<500 words? JS shell?]
                       │ yes
                       ▼
                fetch_playwright (Chromium)
                       │
       ┌───────────────┘
       ▼
extract_listings (LLM, json_mode) ──► [valid?] ── no (≤3 retries) ──► retry
                                          │ yes
                                          ▼
                                  check_pagination
                                          │
                                  has next page?
                                       ├ yes → fetch_simple (next page)
                                       └ no  → END
```

The `extractor` role LLM parses arbitrary HTML — no brittle CSS selectors. The graph is implemented with `langgraph.StateGraph`; if `langgraph` isn't installed (e.g. constrained environment) a sequential fallback drives the same nodes in the same order. Same external interface: `run_scraper_graph(url, llm, *, max_pages) -> list[ExtractedListing]`.

### 4.2 Parse → Score in batches of 5

`worker/tasks/run_pipeline.run_pipeline_url`:

1. Run the scraper graph against the user's URL.
2. Process the resulting listings in batches of `BATCH_SIZE` (default 5):
   - upsert by `(user_id, source, source_key)` — dedup across runs (same idea as the SHA-256 dedup pattern in [factory guide §8](../ingest_and_llm_factory_guide.md#8-sha-256-dedup-guard), applied to listing keys instead of files).
   - parse → score with the cheap `scorer` model.
   - If score is in the borderline band (`LOW < s < THRESHOLD`), re-score with `scorer_strong`. The borderline band is exactly where extra spend buys real signal.
3. `jobs.progress` is updated after each batch — the UI sees results stream in.
4. Auto-create `Application(status=REVIEWING)` for any score ≥ threshold. Discard below the low threshold.

### 4.3 Cover letter — generate + chat refine + email body

A single `CoverLetter` row per application holds:

- `body_markdown` — current full letter.
- `chat_history` — JSON list of `{role, content, at}` turns.
- `email_subject` + `email_body` — populated by `POST /email-draft`.

Endpoints (all sync, single LLM call each):

| Method | Path                                              | Action                                                     |
| ------ | ------------------------------------------------- | ---------------------------------------------------------- |
| POST   | `/api/applications/:id/cover-letter`              | Generate initial draft from CV + listing template          |
| POST   | `/api/applications/:id/cover-letter/chat`         | Refine via natural-language instruction                    |
| GET    | `/api/applications/:id/cover-letter`              | Read current letter + history                              |
| GET    | `/api/applications/:id/cover-letter/download`     | Download as `.md`                                          |
| POST   | `/api/applications/:id/email-draft`               | Generate outreach email body (subject + plain-text body)   |

Refinement goes through the `refiner` role (free-text, temperature 0.3); the LLM returns a JSON `{letter, reply}` so the full updated Markdown and a short acknowledgement come back atomically.

### 4.4 Deep-dive — LangGraph research agent

`worker/pipeline/deepdive/research_graph.py` implements the graph from [phd copilot.md → Agent 2](../phd%20copilot.md#agent-2--deep-dive-research-agent):

```
find_lab_url → fetch_lab_page → extract_research_info → find_publications
            → fetch_abstracts → identify_overlap → draft_email → check_quality
                                                                      │
                                            specific ────────────────►END
                                            generic  → identify_overlap (≤2 retries)
```

Hard rules from the spec are enforced in code:

- `Contact.email = None` always — never auto-stored. The user adds it later via `PATCH /api/outreach/:id`.
- The output is always a draft. The user reviews and sends from their own mail client.
- `check_quality` looks for at least one concrete publication title or overlap term in the draft; bounces back to `identify_overlap` up to 2 times.

---

## 5. CV upload

`POST /api/profile/cv` with `multipart/form-data`. The endpoint:

1. Hashes the file bytes (SHA-256) and writes to `storage/cvs/user_<id>/<sha>.<ext>`.
2. Extracts text via `worker/pipeline/cv/extract.py` — `pypdf` for PDF, `python-docx` for DOCX, raw read for TXT/MD. Both libraries are lazy-imported (factory guide §2 "Load" pattern) so they only load when the corresponding format is actually used.
3. Stores `cv_text`, `cv_filename`, `cv_sha256`, `cv_path` on the `Profile` row.

Once uploaded, `cv_text` is fed to the scorer and the cover-letter drafter through the standard profile payload — that's what makes the system "CV-driven scoring" rather than "interests-keyword scoring".

---

## 6. The job system

Slow operations go through the `jobs` table:

```
POST /api/runs/url {url:...}     ────►  jobs row (status=queued, type=run_pipeline_url)
                                          │
                                          ├─ BackgroundTasks → worker.tasks.run_pipeline.run_pipeline_url
                                          │     • scraper agent (LangGraph)
                                          │     • parse + score in batches of 5
                                          │     • progress updates per batch
                                          ▼
                                  status=done | failed
```

The frontend polls `GET /api/jobs/:id` every 800ms via TanStack Query's `refetchInterval`. On `done`, it invalidates `listings`, `applications`, and `dashboard` query keys.

The same job pattern drives `POST /api/deepdive` (LangGraph deep-dive agent). The cover-letter endpoints are sync — a single LLM call, no job overhead.

---

## 7. State machine

```
NEW → REVIEWING → SHORTLISTED → DRAFTING → READY → APPLIED
          ↓                                          ↓
       DISCARDED                          INTERVIEW   REJECTED
                                              ↓
                                            OFFER / REJECTED
```

Plus `WITHDRAWN` (any time) and `EXPIRED` (deadline passed before APPLIED). Enforced once in `services/state_machine.py:check_transition`. Notable guard: `* → READY` requires every docs_checklist item to have `ready=true`.

Auto-transitions:

- Pipeline auto-creates `REVIEWING` rows (score ≥ threshold).
- `POST /cover-letter` auto-moves `REVIEWING/SHORTLISTED → DRAFTING`.
- Everything else is user-driven (drag a Kanban card → PATCH with the new status).

---

## 8. End-to-end flow

1. User registers, uploads CV (`POST /api/profile/cv`), fills out interests.
2. User pastes a listing URL into the dashboard: `POST /api/runs/url {url}`.
3. The scraper agent fetches the page (Playwright fallback if JS shell), LLM-extracts listings, paginates.
4. Each batch of 5 listings is parsed + scored; `jobs.progress` ticks up.
5. Listings with score ≥ threshold auto-promote to `REVIEWING` applications.
6. User opens an application, hits **Generate cover letter** — sync POST, gets a Markdown draft back.
7. User chats: *"make it more concise"* → `POST /cover-letter/chat` → letter updates, a turn is appended to `chat_history`.
8. User hits **Draft outreach email** → `POST /email-draft` → subject + body populated on the same `CoverLetter` row.
9. For spontaneous outreach: `POST /api/deepdive` with a professor name. Deep-dive LangGraph agent researches the lab, drafts a personalised email. User reviews, manually fills in the prof's email via `PATCH /api/outreach/:id`, sends from their own mail client.

---

## 9. Run it

Local dev (PostgreSQL via Docker, stub LLM by default — no API key needed):

```bash
poetry install
docker compose up -d postgres redis
cp .env.example .env
poetry run alembic upgrade head
make backend                    # API on :8000, /docs is Swagger
cd frontend && npm install && npm run dev   # UI on :5173
```

Optional: `poetry install --extras playwright && poetry run playwright install chromium` for JS-shell scrape fallback.

Switch to real Claude:

```env
LLM__PROVIDER=anthropic
LLM__API_KEY=sk-ant-...
# or use the legacy single-var form:
ANTHROPIC_API_KEY=sk-ant-...
```

Production-shaped:

```bash
docker compose up --build
```

---

## 10. What's stubbed and where the seams are

| Concern              | Today                                                        | Real swap                                                       |
| -------------------- | ------------------------------------------------------------ | --------------------------------------------------------------- |
| Scraper              | LangGraph agent w/ httpx + BS4; Playwright optional          | `pip install playwright && playwright install chromium`         |
| LLM                  | `LLM__PROVIDER=stub` (deterministic, no SDK, no network)     | Set `LLM__PROVIDER=anthropic` + `LLM__API_KEY`                  |
| Job runner           | `BackgroundTasks` in-process                                 | Move task functions to arq workers; signatures unchanged        |
| Cover-letter PDF     | Markdown body served as text/markdown                        | Add Typst install to worker image + render step                 |
| Migrations           | Alembic (`migrations/`) + idempotent `create_all` as dev fallback | `poetry run alembic upgrade head`                              |
| Deep-dive web search | LLM prompted for lab URL                                     | Wire up Tavily / OpenAlex / Semantic Scholar in `find_lab_url`  |

Each row is one localised change; nothing cascades.

---

## 11. The principles driving the shape

- **Pipeline first, agent second** — LangGraph only where conditional branching + retry are real (scraper, deep-dive). Parse/score/draft/refine stay deterministic.
- **Store raw, parse later** — the scraper writes raw text to `storage/raw/` before parsing. Re-run the parser without re-scraping.
- **Human in the loop at send** — system drafts everything, user sends. No auto-apply, no auto-email, ever. Deep-dive never stores an email automatically.
- **Quality over volume** — borderline rescoring with the stronger model is exactly where extra spend buys signal.
- **Universal over hardcoded** — LLM-based listing extraction means any listing site works, not just ones you wrote selectors for.
- **Idempotent + deduplicated** — listings keyed by `(source, source_key)`; CV keyed by SHA-256.
- **Provider over coupling** — every LLM call goes through the factory; swap providers from `.env`.
- **Lazy SDK imports** — only the chosen provider's SDK is imported at runtime; everything else is dead code on disk.
- **Error translation per provider** — pipeline code catches `LLMError`, not one exception type per SDK.

The code is shaped to make these defaults — not constraints you have to remember.
