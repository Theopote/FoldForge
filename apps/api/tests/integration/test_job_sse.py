"""SSE job progress streams."""

from __future__ import annotations

import asyncio
import json

from datetime import datetime, timezone

import pytest

from app.schemas.job import JobStatus
from app.schemas.model import ProjectSettings, ProjectStatus, SourceType
from app.schemas.process_job import ProcessJob
from app.services.process_job_store import process_job_store


def _minimal_process_job(job_id: str = "ssejob001", project_id: str = "proj001") -> ProcessJob:
    now = datetime.now(timezone.utc)
    return ProcessJob(
        id=job_id,
        projectId=project_id,
        settings=ProjectSettings(
            paperSize="A4",
            difficulty="standard",
            style="low_poly",
            targetHeightMm=80,
            addTabs=False,
            addNumbers=True,
            addFoldLines=True,
            addCutLines=True,
            colorMode="line_art",
        ),
        projectName="SSE Test",
        sourcePath="/tmp/model.stl",
        createdAt=now,
        updatedAt=now,
        status=JobStatus.QUEUED,
        progress=0,
        message="Queued",
    )


@pytest.mark.asyncio
async def test_job_event_hub_delivers_payload() -> None:
    from app.services.job_events import JobEventHub

    hub = JobEventHub()
    hub.set_event_loop(asyncio.get_running_loop())
    queue = await hub.subscribe("job123")

    hub.publish("job123", {"status": "running", "progress": 10, "message": "Step"})
    await asyncio.sleep(0.05)

    payload = queue.get_nowait()
    assert payload["progress"] == 10


@pytest.mark.asyncio
async def test_process_job_sse_stream_delivers_updates(
    api_client,
    test_env,
) -> None:
    from app.services.project_store import project_store

    project_store.create(
        project_id="proj001",
        name="SSE",
        source_type=SourceType.UPLOAD_3D,
        source_file_url="/storage/uploads/test.stl",
        status=ProjectStatus.PROCESSING,
    )

    job = _minimal_process_job()
    process_job_store.create(job)

    events: list[dict] = []

    async def read_stream() -> None:
        async with api_client.stream("GET", f"/api/process-jobs/{job.id}/events") as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = json.loads(line.removeprefix("data: "))
                events.append(payload)
                if payload.get("status") == "completed":
                    break

    async def push_updates() -> None:
        await asyncio.sleep(0.35)
        process_job_store.update(
            job.id,
            status=JobStatus.RUNNING,
            progress=40,
            message="Unfolding",
        )
        await asyncio.sleep(0.25)
        process_job_store.update(
            job.id,
            status=JobStatus.COMPLETED,
            progress=100,
            message="Done",
        )

    await asyncio.wait_for(
        asyncio.gather(read_stream(), push_updates()),
        timeout=10.0,
    )

    assert events[0]["status"] == "queued"
    statuses = [event["status"] for event in events]
    assert "running" in statuses
    assert statuses[-1] == "completed"


@pytest.mark.asyncio
async def test_job_sse_unknown_job_returns_404(api_client) -> None:
    response = await api_client.get("/api/jobs/doesnotexist000/events")
    assert response.status_code == 404
