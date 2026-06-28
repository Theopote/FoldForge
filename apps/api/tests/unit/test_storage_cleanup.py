"""Storage cleanup task tests."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.db.database import Database
from app.schemas.job import JobStatus
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, ProjectStatus, SourceType, Style
from app.schemas.process_job import ProcessJob
from app.services.project_store import ProjectStore
from app.services.storage_cleanup import run_storage_cleanup
from app.utils.file_utils import build_storage_url


@pytest.fixture
def cleanup_env(tmp_path, monkeypatch: pytest.MonkeyPatch):
    storage_root = tmp_path / "storage"
    uploads = storage_root / "uploads"
    processed = storage_root / "processed"
    exports = storage_root / "exports"
    for directory in (uploads, processed, exports):
        directory.mkdir(parents=True)

    db_path = storage_root / "test.db"
    test_db = Database(db_path)
    monkeypatch.setattr("app.services.storage_cleanup.database", test_db)
    monkeypatch.setattr("app.services.project_store.database", test_db)

    from app.config import settings

    monkeypatch.setattr(settings, "storage_root", storage_root)
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "processed_dir", processed)
    monkeypatch.setattr(settings, "exports_dir", exports)
    monkeypatch.setattr(settings, "storage_file_ttl_days", 7)

    return {
        "storage_root": storage_root,
        "uploads": uploads,
        "processed": processed,
        "exports": exports,
        "project_store": ProjectStore(),
    }


def _touch_old(path: Path, *, age_days: float = 10) -> None:
    path.write_bytes(b"data")
    old = time.time() - age_days * 86400
    os.utime(path, (old, old))


def test_cleanup_deletes_old_unreferenced_file(cleanup_env) -> None:
    orphan = cleanup_env["uploads"] / "orphan.stl"
    _touch_old(orphan)

    result = run_storage_cleanup(now=time.time())

    assert not orphan.exists()
    assert result.deleted == 1
    assert result.protected == 0


def test_cleanup_keeps_referenced_project_file(cleanup_env) -> None:
    uploads: Path = cleanup_env["uploads"]
    project_store: ProjectStore = cleanup_env["project_store"]

    source = uploads / "abc123.stl"
    _touch_old(source)
    source_url = build_storage_url(Path("uploads") / source.name)

    project_store.create(
        "abc123",
        "Cube",
        source_type=SourceType.UPLOAD_3D,
        source_file_url=source_url,
        status=ProjectStatus.UPLOADED,
    )

    result = run_storage_cleanup(now=time.time())

    assert source.exists()
    assert result.deleted == 0
    assert result.protected == 1


def test_cleanup_keeps_young_orphan(cleanup_env) -> None:
    orphan = cleanup_env["exports"] / "fresh.svg"
    orphan.write_bytes(b"<svg></svg>")

    result = run_storage_cleanup(now=time.time())

    assert orphan.exists()
    assert result.deleted == 0
    assert result.skipped_young == 1


def test_cleanup_protects_incomplete_process_job_source(cleanup_env) -> None:
    uploads: Path = cleanup_env["uploads"]
    source = uploads / "jobsrc.stl"
    _touch_old(source)

    now = datetime.now(timezone.utc)
    payload = ProcessJob(
        id="job001",
        projectId="proj001",
        status=JobStatus.RUNNING,
        settings=ProjectSettings(
            paperSize=PaperSize.A4,
            difficulty=Difficulty.EASY,
            style=Style.LOW_POLY,
            targetHeightMm=80.0,
        ),
        projectName="Test",
        sourcePath=str(source.resolve()),
        createdAt=now,
        updatedAt=now,
    )

    from app.services.storage_cleanup import database

    with database.connection() as conn:
        conn.execute(
            """
            INSERT INTO projects (id, data, created_at, updated_at)
            VALUES ('proj001', '{}', ?, ?)
            """,
            (now.isoformat(), now.isoformat()),
        )
        conn.execute(
            """
            INSERT INTO process_jobs (
                id, project_id, data, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.id,
                payload.project_id,
                json.dumps(payload.model_dump(mode="json", by_alias=True)),
                payload.status.value,
                now.isoformat(),
                now.isoformat(),
            ),
        )

    result = run_storage_cleanup(now=time.time())

    assert source.exists()
    assert result.deleted == 0
    assert result.protected == 1


def test_cleanup_skips_gitkeep(cleanup_env) -> None:
    gitkeep = cleanup_env["uploads"] / ".gitkeep"
    _touch_old(gitkeep, age_days=30)

    result = run_storage_cleanup(now=time.time())

    assert gitkeep.exists()
    assert result.scanned == 0
