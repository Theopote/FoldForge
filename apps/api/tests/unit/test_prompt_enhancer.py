"""Prompt enhancer endpoint tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_enhance_prompt_fallback_without_claude(test_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/ai/enhance-prompt",
            json={"prompt": "paper fox", "style": "low_poly", "difficulty": "easy"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert "paper fox" in body["enhancedPrompt"].lower()
    assert body["tip"]


@pytest.mark.asyncio
async def test_enhance_prompt_uses_claude_when_configured(
    test_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(settings, "claude_prompt_enhance_enabled", True)

    async def fake_complete(system: str, user: str, **kwargs: object) -> dict:
        _ = (system, user, kwargs)
        return {
            "enhanced_prompt": "A cute low poly fox papercraft model",
            "recommended_style": "cute",
            "recommended_difficulty": "easy",
            "tip": "适合新手",
        }

    monkeypatch.setattr(
        "app.services.ai.prompt_enhancer.complete_json",
        fake_complete,
    )

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/ai/enhance-prompt",
            json={"prompt": "fox", "style": "low_poly", "difficulty": "standard"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["enhancedPrompt"] == "A cute low poly fox papercraft model"
    assert body["recommendedStyle"] == "cute"
    assert body["recommendedDifficulty"] == "easy"
    assert body["tip"] == "适合新手"
