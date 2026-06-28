"""Process job cancellation API."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.schemas.job import JobStatus


@pytest.mark.asyncio
async def test_cancel_queued_process_job(api_client, fixtures_dir: Path) -> None:
    fixture = fixtures_dir / "cube.stl"
    assert fixture.exists()

    with fixture.open("rb") as handle:
        upload = await api_client.post(
            "/api/upload-model",
            files={"file": ("cube.stl", handle, "model/stl")},
        )
    assert upload.status_code == 200
    project_id = upload.json()["projectId"]

    process = await api_client.post(
        "/api/process-model",
        json={
            "projectId": project_id,
            "settings": {
                "paperSize": "A4",
                "difficulty": "easy",
                "style": "low_poly",
                "targetHeightMm": 80,
                "addTabs": False,
                "addNumbers": True,
                "addFoldLines": True,
                "addCutLines": True,
            },
        },
    )
    assert process.status_code == 202
    job_id = process.json()["jobId"]

    cancel = await api_client.post(f"/api/process-jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    payload = cancel.json()
    assert payload["status"] == JobStatus.CANCELLED.value

    poll = await api_client.get(f"/api/process-jobs/{job_id}")
    assert poll.status_code == 200
    assert poll.json()["status"] == JobStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_cancel_unknown_job_returns_404(api_client) -> None:
    response = await api_client.post("/api/process-jobs/doesnotexist000/cancel")
    assert response.status_code == 404
