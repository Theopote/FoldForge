"""Backward-compatible shim — prefer app.services.llm."""

from __future__ import annotations

from typing import Any

from app.services.llm.json_utils import parse_llm_json as parse_claude_json
from app.services.llm.registry import complete_json, is_llm_available

is_available = is_llm_available


async def claude_complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> str:
    """Deprecated: use app.services.llm.registry.get_llm_provider().complete()."""
    from app.services.llm.registry import get_llm_provider

    provider = get_llm_provider()
    return await provider.complete(
        system,
        user,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def claude_complete_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> dict[str, Any]:
    return await complete_json(
        system,
        user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
