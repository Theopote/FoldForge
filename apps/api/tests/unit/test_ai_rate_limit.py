"""AI generation rate limit tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.services.ai.rate_limit import AiGenerationRateLimiter


def test_token_bucket_allows_burst_then_blocks(test_env) -> None:
    limiter = AiGenerationRateLimiter(capacity=2.0, refill_per_sec=1.0 / 3600.0)

    assert limiter.try_acquire("client-a") is None
    assert limiter.try_acquire("client-a") is None
    retry_after = limiter.try_acquire("client-a")
    assert retry_after is not None
    assert retry_after >= 1


def test_token_bucket_isolates_clients(test_env) -> None:
    limiter = AiGenerationRateLimiter(capacity=1.0, refill_per_sec=0.0)

    assert limiter.try_acquire("client-a") is None
    assert limiter.try_acquire("client-b") is None
    assert limiter.try_acquire("client-a") is not None


@pytest.mark.asyncio
async def test_generate_from_text_skips_limit_for_mock_provider(
    test_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ai_provider", "mock")
    monkeypatch.setattr(settings, "ai_generation_rate_limit_per_hour", 1)
    monkeypatch.setattr(settings, "ai_generation_rate_limit_burst", 1)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for _ in range(3):
            response = await client.post(
                "/api/generate-from-text",
                json={"prompt": "paper cube", "style": "low_poly"},
            )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_from_text_rate_limits_paid_provider(
    test_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "meshy_api_key", "test-meshy-key")
    monkeypatch.setattr(settings, "ai_provider", "meshy")
    monkeypatch.setattr(settings, "ai_generation_rate_limit_per_hour", 1)
    monkeypatch.setattr(settings, "ai_generation_rate_limit_burst", 1)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/api/generate-from-text",
            json={"prompt": "paper cube", "style": "low_poly"},
        )
        second = await client.post(
            "/api/generate-from-text",
            json={"prompt": "paper cube", "style": "low_poly"},
        )

    assert first.status_code == 202
    assert second.status_code == 429
    assert "Retry-After" in second.headers
    assert "rate limit" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_rate_limit_is_per_api_key(
    test_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "meshy_api_key", "test-meshy-key")
    monkeypatch.setattr(settings, "ai_provider", "meshy")
    monkeypatch.setattr(settings, "ai_generation_rate_limit_per_hour", 1)
    monkeypatch.setattr(settings, "ai_generation_rate_limit_burst", 1)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        first_client = await client.post(
            "/api/generate-from-text",
            json={"prompt": "paper cube", "style": "low_poly"},
            headers={"X-API-Key": "client-a"},
        )
        first_client_again = await client.post(
            "/api/generate-from-text",
            json={"prompt": "paper cube", "style": "low_poly"},
            headers={"X-API-Key": "client-a"},
        )
        other_client = await client.post(
            "/api/generate-from-text",
            json={"prompt": "paper house", "style": "low_poly"},
            headers={"X-API-Key": "client-b"},
        )

    assert first_client.status_code == 202
    assert first_client_again.status_code == 429
    assert other_client.status_code == 202
