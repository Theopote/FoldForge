"""Select and invoke configured LLM providers."""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.llm.base import LlmProvider
from app.services.llm.json_utils import parse_llm_json
from app.services.llm.providers.claude import ClaudeLlmProvider
from app.services.llm.providers.mock import MockLlmProvider
from app.services.llm.providers.openai import OpenAiLlmProvider

_PROVIDERS: dict[str, type[LlmProvider]] = {
    "claude": ClaudeLlmProvider,
    "openai": OpenAiLlmProvider,
    "mock": MockLlmProvider,
}


def resolve_llm_provider_name() -> str:
    """Resolve configured LLM backend (`auto` prefers Claude, then OpenAI)."""
    configured = settings.llm_provider.lower()
    if configured != "auto":
        return configured

    if settings.anthropic_api_key:
        return "claude"
    if settings.openai_api_key:
        return "openai"
    return "mock"


def get_llm_provider(name: str | None = None) -> LlmProvider:
    provider_name = name or resolve_llm_provider_name()
    cls = _PROVIDERS.get(provider_name, MockLlmProvider)
    return cls()


def is_llm_available() -> bool:
    """Return True when a production LLM provider is configured."""
    name = resolve_llm_provider_name()
    if name == "mock":
        return False
    provider = get_llm_provider(name)
    return provider.is_available


def list_llm_providers() -> list[dict[str, str | bool]]:
    """Return LLM provider status for diagnostics and future API listing."""
    active_name = resolve_llm_provider_name()
    items: list[dict[str, str | bool]] = []

    for name in ("claude", "openai", "mock"):
        provider = get_llm_provider(name)
        configured = provider.is_available if name != "mock" else True
        reason = ""
        if name == "claude" and not settings.anthropic_api_key:
            reason = "Set ANTHROPIC_API_KEY"
        elif name == "openai" and not settings.openai_api_key:
            reason = "Set OPENAI_API_KEY"
        elif name == "mock":
            reason = "Offline fallback when no LLM credentials are configured"

        items.append(
            {
                "name": name,
                "active": active_name == name,
                "available": provider.is_available,
                "configured": configured,
                "reason": reason,
            }
        )

    items.append(
        {
            "name": "auto",
            "active": settings.llm_provider.lower() == "auto",
            "available": is_llm_available(),
            "configured": True,
            "reason": f"Resolved to {active_name}",
        }
    )
    return items


async def complete_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Run a single-turn completion and parse JSON from the response."""
    provider = get_llm_provider()
    if not provider.is_available:
        raise RuntimeError(f"LLM provider '{provider.name}' is not configured.")

    raw = await provider.complete(
        system,
        user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return parse_llm_json(raw)
