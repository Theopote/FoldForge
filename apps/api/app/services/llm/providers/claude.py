"""Anthropic Claude LLM provider."""

from __future__ import annotations

import httpx

from app.config import settings
from app.services.llm.base import LlmProvider

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class ClaudeLlmProvider(LlmProvider):
    name = "claude"

    @property
    def is_available(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

        payload = {
            "model": settings.claude_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        blocks = data.get("content", [])
        texts = [block["text"] for block in blocks if block.get("type") == "text"]
        return "\n".join(texts).strip()
