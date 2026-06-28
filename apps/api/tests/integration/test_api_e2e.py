"""End-to-end API: upload model and run papercraft processing."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import settings
from tests.conftest import wait_for_process_job


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_upload_and_process_cube(api_client, fixtures_dir: Path) -> None:
    fixture = fixtures_dir / "cube.stl"
    assert fixture.exists()

    with fixture.open("rb") as handle:
        upload_response = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )
    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    project_id = upload_data["projectId"]
    assert upload_data["status"] == "uploaded"

    process_response = await api_client.post(
        "/api/process-model",
        json={
            "projectId": project_id,
            "settings": {
                "paperSize": "A4",
                "difficulty": "standard",
                "style": "low_poly",
                "targetHeightMm": 100,
                "addTabs": True,
                "addNumbers": True,
                "addFoldLines": True,
                "addCutLines": True,
            },
        },
    )
    assert process_response.status_code == 202
    job_id = process_response.json()["jobId"]

    job = await wait_for_process_job(api_client, job_id)
    assert job["status"] == "completed", job.get("error")
    assert job["progress"] == 100
    assert job["unfoldSvgUrl"]
    assert job["unfoldPdfUrl"]
    assert job["stats"]["pieces"] >= 1

    project_response = await api_client.get(f"/api/projects/{project_id}")
    assert project_response.status_code == 200
    project = project_response.json()
    assert project["status"] == "ready"

    svg_path = settings.exports_dir / f"{project_id}.svg"
    pdf_path = settings.exports_dir / f"{project_id}.pdf"
    assert svg_path.exists()
    assert pdf_path.exists()
    assert svg_path.stat().st_size > 500
    assert pdf_path.read_bytes()[:4] == b"%PDF"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_and_root(api_client) -> None:
    health = await api_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    root = await api_client.get("/")
    assert root.status_code == 200
    assert root.json()["name"]
