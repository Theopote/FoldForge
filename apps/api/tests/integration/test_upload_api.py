"""Upload API tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_upload_model_returns_project(api_client, fixtures_dir: Path) -> None:
    fixture = fixtures_dir / "cube.stl"
    assert fixture.exists()

    with fixture.open("rb") as handle:
        response = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["projectId"]
    assert payload["sourceFileUrl"].startswith("/storage/uploads/")
    assert payload["status"] == "uploaded"

    project = await api_client.get(f"/api/projects/{payload['projectId']}")
    assert project.status_code == 200
    assert project.json()["id"] == payload["projectId"]


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_format(api_client) -> None:
    response = await api_client.post(
        "/api/upload-model",
        files={"file": ("model.blend", b"fake", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported" in response.json()["detail"]
