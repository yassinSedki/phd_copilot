"""LLM factory. Single entry point `get_llm(settings, role)`; provider class
is loaded lazily via importlib so the chosen provider's SDK is the ONLY one
imported at runtime (factory guide §9).

Add a new provider in one step: write `providers/<name>.py` with a class
that subclasses `LLMClient`, then add one row to `_PROVIDER_REGISTRY`.
"""

from __future__ import annotations

import importlib
from typing import Any

from shared.llm.base import LLMClient
from shared.llm.errors import LLMError, LLMErrorCode

# (module path, class name) — both lazy-loaded.
_PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "stub": ("shared.llm.providers.stub", "StubLLMClient"),
    "anthropic": ("shared.llm.providers.anthropic", "AnthropicLLMClient"),
    "cohere": ("shared.llm.providers.cohere", "CohereChatProvider"),
}

# Roles whose output is free-form prose. Everything else gets json_mode=True
# when the provider supports it.
FREE_TEXT_ROLES = {"summarizer", "generator", "synthesizer", "refiner"}


def _role_temperature(settings: Any, role: str) -> float:
    return float(getattr(settings, f"temperature_{role}", 0.1))


def _role_model(settings: Any, role: str) -> str:
    default = getattr(settings, "default_model", "claude-sonnet-4-6")
    role_models: dict[str, str] = getattr(settings, "role_models", {}) or {}
    return role_models.get(role, default)


def get_llm(settings: Any, role: str = "builder") -> LLMClient:
    """Build an LLMClient for the given role.

    `settings` is the nested LLM settings block (see app.config.LLMSettings).
    Role-derived parameters: model + temperature + json_mode. The provider
    receives only what it needs; nothing else.
    """

    provider_name = (getattr(settings, "provider", "") or "stub").lower()
    if provider_name not in _PROVIDER_REGISTRY:
        raise LLMError(
            LLMErrorCode.PROVIDER_ERROR,
            f"Provider {provider_name!r} not registered. Add to _PROVIDER_REGISTRY.",
        )

    module_path, class_name = _PROVIDER_REGISTRY[provider_name]
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # missing extras for that provider
        raise LLMError(
            LLMErrorCode.PROVIDER_ERROR,
            f"Cannot import provider {provider_name!r}: {exc}",
        ) from exc

    provider_cls = getattr(module, class_name)

    return provider_cls(
        api_key=getattr(settings, "api_key", "") or "",
        model=_role_model(settings, role),
        temperature=_role_temperature(settings, role),
        max_tokens=int(getattr(settings, "max_tokens", 2048)),
        timeout=int(getattr(settings, "request_timeout", 60)),
        json_mode=role not in FREE_TEXT_ROLES,
    )
