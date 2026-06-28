"""Seam toggle API integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_patch_project_seams_requires_ready_project(api_client, fixtures_dir: Path) -> None:
    with (fixtures_dir / "cube.stl").open("rb") as handle:
        upload = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )
    project_id = upload.json()["projectId"]

    response = await api_client.patch(
        f"/api/projects/{project_id}/seams",
        json={"toggle": {"meshEdge": "0,1"}},
    )
    assert response.status_code == 400
    assert "ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_project_seams_unknown_project_returns_404(api_client) -> None:
    response = await api_client.patch(
        "/api/projects/doesnotexist000/seams",
        json={"toggle": {"meshEdge": "0,1"}},
    )
    assert response.status_code == 404
