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


@pytest.mark.asyncio
async def test_cancel_terminal_process_job_returns_current_state(
    api_client, fixtures_dir: Path
) -> None:
    from app.schemas.model import ProjectStatus
    from app.services.process_job_store import process_job_store

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

    process_job_store.update(
        job_id,
        status=JobStatus.COMPLETED,
        progress=100,
        message="Complete",
        result_status=ProjectStatus.READY,
    )

    cancel = await api_client.post(f"/api/process-jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == JobStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_cancel_running_process_job(
    api_client,
    monkeypatch: pytest.MonkeyPatch,
    fixtures_dir: Path,
) -> None:
    import asyncio
    import time

    import app.services.process_queue as process_queue_module
    from app.services.pipeline_errors import JobCancelledError
    from tests.conftest import wait_for_process_job

    started = asyncio.Event()

    def slow_run_pipeline(*_args, cancel_check=None, on_progress=None, **_kwargs):
        started.set()
        while True:
            if cancel_check is not None and cancel_check():
                raise JobCancelledError("Processing cancelled.")
            if on_progress is not None:
                on_progress(15, "Slow step")
            time.sleep(0.02)

    monkeypatch.setattr(process_queue_module, "run_pipeline", slow_run_pipeline)

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

    await asyncio.wait_for(started.wait(), timeout=15.0)

    for _ in range(100):
        poll = await api_client.get(f"/api/process-jobs/{job_id}")
        poll.raise_for_status()
        if poll.json()["status"] == JobStatus.RUNNING.value:
            break
        await asyncio.sleep(0.05)
    else:
        pytest.fail("Process job did not enter running state")

    cancel = await api_client.post(f"/api/process-jobs/{job_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["cancelRequested"] is True

    job = await wait_for_process_job(api_client, job_id, timeout_sec=30.0)
    assert job["status"] == JobStatus.CANCELLED.value

    project = await api_client.get(f"/api/projects/{project_id}")
    assert project.status_code == 200
    payload = project.json()
    assert payload["status"] != "ready"
    assert not payload.get("unfoldPdfUrl")
    assert not payload.get("unfoldSvgUrl")
