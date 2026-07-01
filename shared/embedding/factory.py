"""Embedding factory — singleton with reset (factory guide §11).

Unlike the LLM factory (returns a new instance per call), the embedding
factory is a true singleton because providers hold an LRU cache. A new
instance would start with an empty cache on every call.
"""

from __future__ import annotations

import importlib
from typing import Optional

from shared.embedding.base import EmbeddingProvider
from shared.llm.errors import LLMError, LLMErrorCode

_PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "stub": ("shared.embedding.providers.stub", "StubEmbeddingProvider"),
    "cohere": ("shared.embedding.providers.cohere", "CohereEmbeddingProvider"),
}

_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider(settings=None) -> EmbeddingProvider:
    """Return the process-wide embedding provider singleton."""

    global _instance
    if _instance is not None:
        return _instance

    if settings is None:
        from shared.config import get_settings

        settings = get_settings().embedding

    provider_name = (getattr(settings, "provider", "") or "stub").lower()
    if provider_name not in _PROVIDER_REGISTRY:
        raise LLMError(
            LLMErrorCode.PROVIDER_ERROR,
            f"Embedding provider {provider_name!r} not registered.",
        )

    module_path, class_name = _PROVIDER_REGISTRY[provider_name]
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:
        raise LLMError(
            LLMErrorCode.PROVIDER_ERROR,
            f"Cannot import embedding provider {provider_name!r}: {exc}",
        ) from exc

    cls = getattr(module, class_name)
    _instance = cls(settings)
    return _instance


def reset_embedding_provider() -> None:
    """Drop the cached instance — for tests that swap in a mock provider."""

    global _instance
    _instance = None
