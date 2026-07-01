"""Offline LLM provider used when no API credentials are configured."""

from __future__ import annotations

from app.services.llm.base import LlmProvider


class MockLlmProvider(LlmProvider):
    name = "mock"

    @property
    def is_available(self) -> bool:
        return True

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        _ = (system, user, max_tokens, temperature)
        raise RuntimeError("LLM provider 'mock' does not support completions.")
