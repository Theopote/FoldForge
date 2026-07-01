"""OpenAI-compatible chat completions LLM provider."""

from __future__ import annotations

import httpx

from app.config import settings
from app.services.llm.base import LlmProvider


def _chat_completions_url() -> str:
    base = settings.openai_base_url.rstrip("/")
    return f"{base}/chat/completions"


class OpenAiLlmProvider(LlmProvider):
    name = "openai"

    @property
    def is_available(self) -> bool:
        return bool(settings.openai_api_key)

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": settings.openai_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                _chat_completions_url(),
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI response contained no choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenAI response contained no text content.")
        return content.strip()
