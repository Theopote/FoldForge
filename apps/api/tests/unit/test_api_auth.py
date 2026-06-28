"""API key authentication tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings


@pytest.fixture
def api_key_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "api_key", "test-secret-key")
    monkeypatch.setattr(settings, "require_api_auth", False)


@pytest.mark.asyncio
async def test_health_is_public(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_rejects_missing_key(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/projects/doesnotexist")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_accepts_bearer_key(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/projects/doesnotexist",
            headers={"Authorization": "Bearer test-secret-key"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_accepts_x_api_key_header(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/api/projects/doesnotexist",
            headers={"X-API-Key": "test-secret-key"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_storage_rejects_missing_key(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/storage/uploads/missing.glb")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_storage_accepts_access_token_query(api_key_env) -> None:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/storage/uploads/missing.glb?access_token=test-secret-key",
        )
    assert response.status_code == 404
