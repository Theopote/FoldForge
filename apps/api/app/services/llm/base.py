"""LLM provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class LlmProvider(ABC):
    """Single-turn text completion for instructions, prompts, and advisors."""

    name: str

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True when credentials and model config are present."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Return raw assistant text."""
