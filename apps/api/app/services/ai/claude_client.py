"""Anthropic Claude API client — shared across all AI features."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def _headers() -> dict[str, str]:
    return {
        "x-api-key": settings.anthropic_api_key or "",
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }


async def claude_complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> str:
    """Single-turn completion. Returns the text content."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured.")

    payload = {
        "model": settings.claude_model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            ANTHROPIC_API_URL,
            headers=_headers(),
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    blocks = data.get("content", [])
    texts = [block["text"] for block in blocks if block.get("type") == "text"]
    return "\n".join(texts).strip()


def is_available() -> bool:
    return bool(settings.anthropic_api_key)


def parse_claude_json(raw: str) -> dict[str, Any]:
    """Parse JSON from Claude output, stripping optional markdown fences."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)
