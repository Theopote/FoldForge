"""Worker restart and lease recovery tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.database import Database
from app.schemas.generation_job import GenerationJob, JobType
from app.schemas.job import JobStatus
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style
from app.schemas.process_job import ProcessJob
from app.services.ai.generation_queue import GenerationQueue
from app.services.ai.job_store import GenerationJobStore
from app.services.process_job_store import ProcessJobStore
from app.services.process_queue import ProcessQueue


@pytest.fixture
def queue_env(tmp_path, monkeypatch: pytest.MonkeyPatch):
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    test_db = Database(storage_root / "test.db")

    monkeypatch.setattr("app.services.process_job_store.database", test_db)
    monkeypatch.setattr("app.services.ai.job_store.database", test_db)

    return {
        "process_store": ProcessJobStore(),
        "generation_store": GenerationJobStore(),
        "process_queue": ProcessQueue(),
        "generation_queue": GenerationQueue(),
    }


def _process_job(job_id: str = "proc001", project_id: str = "proj001") -> ProcessJob:
    now = datetime.now(timezone.utc)
    return ProcessJob(
        id=job_id,
        projectId=project_id,
        status=JobStatus.RUNNING,
        settings=ProjectSettings(
            paperSize=PaperSize.A4,
            difficulty=Difficulty.EASY,
            style=Style.LOW_POLY,
            targetHeightMm=80.0,
        ),
        projectName="Test",
        sourcePath="/tmp/model.stl",
        lockedBy="dead-worker",
        lockedUntil=now + timedelta(hours=1),
        createdAt=now,
        updatedAt=now,
    )


def _generation_job(job_id: str = "gen001", project_id: str = "proj001") -> GenerationJob:
    now = datetime.now(timezone.utc)
    return GenerationJob(
        id=job_id,
        projectId=project_id,
        jobType=JobType.TEXT_TO_3D,
        status=JobStatus.RUNNING,
        provider="mock",
        prompt="cube",
        output_path="/tmp/out.glb",
        progress=42,
        message="Generating",
        createdAt=now,
        updatedAt=now,
    )


def test_prepare_for_recovery_clears_active_process_lease(queue_env) -> None:
    store: ProcessJobStore = queue_env["process_store"]
    job = _process_job()
    store.create(job)

    prepared = store.prepare_for_recovery(job.id)
    assert prepared is not None
    assert prepared.status == JobStatus.QUEUED
    assert prepared.locked_by is None
    assert prepared.locked_until is None
    assert any(item.id == job.id for item in store.list_claimable())


@pytest.mark.asyncio
async def test_process_recover_pending_requeues_running_with_active_lease(
    queue_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: ProcessJobStore = queue_env["process_store"]
    queue: ProcessQueue = queue_env["process_queue"]
    enqueued: list[str] = []

    async def capture_enqueue(job_id: str) -> None:
        enqueued.append(job_id)

    monkeypatch.setattr(queue, "enqueue", capture_enqueue)

    job = _process_job()
    store.create(job)

    await queue.recover_pending_jobs()

    assert enqueued == [job.id]
    recovered = store.get(job.id)
    assert recovered is not None
    assert recovered.status == JobStatus.QUEUED
    assert recovered.locked_by is None


def test_prepare_for_recovery_resets_generation_job(queue_env) -> None:
    store: GenerationJobStore = queue_env["generation_store"]
    job = _generation_job()
    store.create(job)

    prepared = store.prepare_for_recovery(job.id)
    assert prepared is not None
    assert prepared.status == JobStatus.QUEUED
    assert prepared.progress == 0


@pytest.mark.asyncio
async def test_process_recover_stale_leases_only_expired_running(
    queue_env,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store: ProcessJobStore = queue_env["process_store"]
    queue: ProcessQueue = queue_env["process_queue"]
    enqueued: list[str] = []

    async def capture_enqueue(job_id: str) -> None:
        enqueued.append(job_id)

    monkeypatch.setattr(queue, "enqueue", capture_enqueue)

    now = datetime.now(timezone.utc)
    expired = _process_job("expired001")
    expired.locked_until = now - timedelta(minutes=5)
    store.create(expired)

    active = _process_job("active001", project_id="proj002")
    active.locked_until = now + timedelta(hours=1)
    store.create(active)

    await queue.recover_stale_leases()

    assert enqueued == ["expired001"]
    active_job = store.get("active001")
    assert active_job is not None
    assert active_job.status == JobStatus.RUNNING
