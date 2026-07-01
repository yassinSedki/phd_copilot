"""Pydantic settings. Single source of truth for config across backend + worker.

Layout follows the factory guide §12 — a top-level `Settings` that nests
`LLMSettings`. Nested env vars use the `LLM__` delimiter:

    LLM__PROVIDER=anthropic
    LLM__ROLE_MODELS__CLASSIFIER=claude-haiku-4-5-20251001
    LLM__TEMPERATURE_BUILDER=0.1

A model_validator propagates ANTHROPIC_API_KEY → llm.api_key so the .env
keeps the one-key convention people expect.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingSettings(BaseModel):
    """Embedding provider + model + cache. Read by `get_embedding_provider()`.

    Defaults: Cohere `embed-english-v3.0`, 1024-dim, 96/batch, 1000-item LRU cache.
    Switch with EMBEDDING__PROVIDER=stub for offline dev.
    """

    provider: str = "stub"
    api_key: str = ""
    model: str = "embed-english-v3.0"
    dim: int = 1024
    batch_size: int = 96
    cache_size: int = 1000


class LLMSettings(BaseModel):
    """Provider, model selection, and per-role tuning. Read by `get_llm()`."""

    provider: str = "stub"
    api_key: str = ""
    request_timeout: int = 60
    max_tokens: int = 2048
    default_model: str = "command-a-03-2025"

    # Per-role model mapping (factory guide §10). Different pipeline steps
    # have different reliability / cost requirements; tune them from .env
    # without touching code. Defaults assume Cohere — switch the values if
    # using Anthropic.
    role_models: dict[str, str] = Field(
        default_factory=lambda: {
            "classifier": "command-r-08-2024",
            "builder": "command-a-03-2025",
            "summarizer": "command-r-08-2024",
            "scorer": "command-r-08-2024",
            "scorer_strong": "command-a-03-2025",
            "drafter": "command-a-03-2025",
            "refiner": "command-a-03-2025",
            "extractor": "command-a-03-2025",
            "researcher": "command-a-03-2025",
            "generator": "command-a-03-2025",
        }
    )

    temperature_classifier: float = 0.0
    temperature_builder: float = 0.1
    temperature_summarizer: float = 0.3
    temperature_scorer: float = 0.0
    temperature_scorer_strong: float = 0.1
    temperature_drafter: float = 0.3
    temperature_refiner: float = 0.3
    temperature_extractor: float = 0.0
    temperature_researcher: float = 0.2
    temperature_generator: float = 0.3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ---- API surface

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 30

    # PostgreSQL is the supported runtime. SQLite remains usable for ad-hoc
    # tests via DATABASE_URL=sqlite:///./local.db, but production + dev both
    # assume Postgres (docker compose brings one up locally).
    database_url: str = "postgresql+psycopg2://phd:phd@localhost:5432/phd"

    storage_dir: Path = Path("./storage")

    # ---- pipeline thresholds

    default_score_threshold: int = 70
    low_score_threshold: int = 40

    # ---- scraper agent

    max_pages_per_url: int = 10
    batch_size: int = 5
    scraper_user_agent: str = "phd-copilot/0.1 (research; +contact@example.org)"
    playwright_enabled: bool = True

    # ---- nested

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)

    # ---- back-compat env vars (single-key convention)

    anthropic_api_key: str = ""
    cohere_api_key: str = ""
    llm_provider: str = ""

    @model_validator(mode="after")
    def _propagate_keys(self) -> "Settings":
        # Convenience: ANTHROPIC_API_KEY / COHERE_API_KEY populate the
        # nested .api_key fields. Whatever the user wrote at the top level
        # wins if both are set.
        if self.anthropic_api_key and not self.llm.api_key:
            self.llm.api_key = self.anthropic_api_key
        if self.cohere_api_key:
            if not self.llm.api_key and self.llm.provider == "cohere":
                self.llm.api_key = self.cohere_api_key
            if not self.embedding.api_key:
                self.embedding.api_key = self.cohere_api_key
        if self.llm_provider and self.llm.provider == "stub":
            self.llm.provider = self.llm_provider
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "raw").mkdir(exist_ok=True)
    (settings.storage_dir / "uploads").mkdir(exist_ok=True)
    (settings.storage_dir / "outputs").mkdir(exist_ok=True)
    (settings.storage_dir / "cvs").mkdir(exist_ok=True)
    return settings
