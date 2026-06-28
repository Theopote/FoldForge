"""Project settings PATCH API."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_patch_project_settings_persists(api_client, fixtures_dir: Path) -> None:
    fixture = fixtures_dir / "cube.stl"
    assert fixture.exists()

    with fixture.open("rb") as handle:
        upload = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )
    assert upload.status_code == 200
    project_id = upload.json()["projectId"]

    patch = await api_client.patch(
        f"/api/projects/{project_id}/settings",
        json={
            "paperSize": "A3",
            "difficulty": "easy",
            "style": "low_poly",
            "targetHeightMm": 90,
            "addTabs": False,
            "addNumbers": True,
            "addFoldLines": True,
            "addCutLines": True,
            "colorMode": "line_art",
        },
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["settings"]["paperSize"] == "A3"
    assert body["settings"]["targetHeightMm"] == 90
    assert body["settings"]["addTabs"] is False

    project = await api_client.get(f"/api/projects/{project_id}")
    assert project.status_code == 200
    assert project.json()["settings"] == body["settings"]


@pytest.mark.asyncio
async def test_patch_project_settings_unknown_project_returns_404(api_client) -> None:
    response = await api_client.patch(
        "/api/projects/doesnotexist000/settings",
        json={
            "paperSize": "A4",
            "difficulty": "standard",
            "style": "low_poly",
            "targetHeightMm": 120,
            "addTabs": True,
            "addNumbers": True,
            "addFoldLines": True,
            "addCutLines": True,
            "colorMode": "line_art",
        },
    )
    assert response.status_code == 404
