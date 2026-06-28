"""Unit tests for process job store write-path optimizations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.db.database import Database
from app.schemas.job import JobStatus
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style
from app.schemas.process_job import ProcessJob
from app.services.process_job_store import ProcessJobStore


def _sample_job(job_id: str = "job001", project_id: str = "proj001") -> ProcessJob:
    now = datetime.now(timezone.utc)
    return ProcessJob(
        id=job_id,
        projectId=project_id,
        status=JobStatus.QUEUED,
        settings=ProjectSettings(
            paperSize=PaperSize.A4,
            difficulty=Difficulty.EASY,
            style=Style.LOW_POLY,
            targetHeightMm=80.0,
        ),
        projectName="Test",
        sourcePath="/tmp/model.stl",
        createdAt=now,
        updatedAt=now,
    )


@pytest.fixture
def job_store(tmp_path, monkeypatch: pytest.MonkeyPatch) -> ProcessJobStore:
    db_path = tmp_path / "jobs.db"
    test_db = Database(db_path)
    monkeypatch.setattr("app.services.process_job_store.database", test_db)

    with test_db.connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, data, created_at, updated_at)
            VALUES ('proj001', '{}', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """
        )

    return ProcessJobStore()


def test_update_uses_single_write_connection(job_store: ProcessJobStore) -> None:
    job = _sample_job()
    job_store.create(job)

    import app.services.process_job_store as store_module

    real_connection = store_module.database.connection
    write_count = 0

    def counting_connection():
        nonlocal write_count
        write_count += 1
        return real_connection()

    with patch.object(store_module.database, "connection", side_effect=counting_connection):
        updated = job_store.update(job.id, progress=42, message="Halfway")

    assert updated is not None
    assert updated.progress == 42
    assert write_count == 1


def test_try_acquire_lock_persists_in_one_transaction(job_store: ProcessJobStore) -> None:
    job = _sample_job()
    job_store.create(job)

    import app.services.process_job_store as store_module

    real_connection = store_module.database.connection
    write_count = 0

    def counting_connection():
        nonlocal write_count
        write_count += 1
        return real_connection()

    with patch.object(store_module.database, "connection", side_effect=counting_connection):
        claimed = job_store.try_acquire_lock(job.id, "worker-a", lease_sec=60)

    assert claimed is not None
    assert claimed.status == JobStatus.RUNNING
    assert claimed.locked_by == "worker-a"
    assert write_count == 1

    stored = job_store.get(job.id)
    assert stored is not None
    assert stored.status == JobStatus.RUNNING
    assert stored.attempts == 1


def test_renew_lock_updates_json_in_same_transaction(job_store: ProcessJobStore) -> None:
    job = _sample_job()
    job_store.create(job)
    assert job_store.try_acquire_lock(job.id, "worker-a", lease_sec=60) is not None

    import app.services.process_job_store as store_module

    real_connection = store_module.database.connection
    write_count = 0

    def counting_connection():
        nonlocal write_count
        write_count += 1
        return real_connection()

    with patch.object(store_module.database, "connection", side_effect=counting_connection):
        assert job_store.renew_lock(job.id, "worker-a", lease_sec=120) is True

    assert write_count == 1
    stored = job_store.get(job.id)
    assert stored is not None
    assert stored.locked_until is not None


def test_is_cancel_requested_reads_without_full_validation(
    job_store: ProcessJobStore,
) -> None:
    job = _sample_job()
    job_store.create(job)
    job_store.update(job.id, cancel_requested=True)

    with patch.object(
        ProcessJob,
        "model_validate",
        side_effect=AssertionError("should not validate full job on cancel check"),
    ):
        assert job_store.is_cancel_requested(job.id) is True


def test_cancel_queued_job_in_single_transaction(job_store: ProcessJobStore) -> None:
    job = _sample_job()
    job_store.create(job)

    import app.services.process_job_store as store_module

    real_connection = store_module.database.connection
    write_count = 0

    def counting_connection():
        nonlocal write_count
        write_count += 1
        return real_connection()

    with patch.object(store_module.database, "connection", side_effect=counting_connection):
        cancelled = job_store.cancel(job.id)

    assert cancelled is not None
    assert cancelled.status == JobStatus.CANCELLED
    assert write_count == 1


def test_update_progress_and_renew_lock_single_transaction(
    job_store: ProcessJobStore,
) -> None:
    job = _sample_job()
    job_store.create(job)
    assert job_store.try_acquire_lock(job.id, "worker-a", lease_sec=60) is not None

    import app.services.process_job_store as store_module

    real_connection = store_module.database.connection
    write_count = 0

    def counting_connection():
        nonlocal write_count
        write_count += 1
        return real_connection()

    with patch.object(store_module.database, "connection", side_effect=counting_connection):
        cancelled = job_store.update_progress_and_renew_lock(
            job.id,
            "worker-a",
            120,
            progress=50,
            message="Halfway",
        )

    assert cancelled is False
    assert write_count == 1

    stored = job_store.get(job.id)
    assert stored is not None
    assert stored.progress == 50
    assert stored.message == "Halfway"


def test_update_progress_detects_cancel_requested_in_same_transaction(
    job_store: ProcessJobStore,
) -> None:
    job = _sample_job()
    job_store.create(job)
    assert job_store.try_acquire_lock(job.id, "worker-a", lease_sec=60) is not None
    job_store.cancel(job.id)

    assert job_store.update_progress_and_renew_lock(
        job.id,
        "worker-a",
        120,
        progress=50,
        message="Halfway",
    ) is True

    stored = job_store.get(job.id)
    assert stored is not None
    assert stored.progress != 50
