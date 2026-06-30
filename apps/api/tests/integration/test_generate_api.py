"""AI generation API validation tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_generate_from_image_rejects_empty_file(api_client) -> None:
    response = await api_client.post(
        "/api/generate-from-image",
        files={"file": ("empty.png", b"", "image/png")},
        data={"style": "low_poly"},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


async def test_generate_from_image_rejects_spoofed_image(api_client) -> None:
    response = await api_client.post(
        "/api/generate-from-image",
        files={"file": ("fake.png", b"not really an image", "image/png")},
        data={"style": "low_poly"},
    )

    assert response.status_code == 400
    assert "does not match" in response.json()["detail"].lower()
