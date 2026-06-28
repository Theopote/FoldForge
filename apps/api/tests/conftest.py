"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.config import settings
from app.db.database import Database
from app.schemas.model import Difficulty, PaperSize, ProjectSettings, Style


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

STORE_MODULES = (
    "app.services.project_store",
    "app.services.process_job_store",
    "app.services.ai.job_store",
)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def default_settings() -> ProjectSettings:
    return ProjectSettings(
        paperSize=PaperSize.A4,
        difficulty=Difficulty.STANDARD,
        style=Style.LOW_POLY,
        targetHeightMm=120.0,
        addTabs=True,
        addNumbers=True,
        addFoldLines=True,
        addCutLines=True,
    )


@pytest.fixture
def test_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated storage paths and SQLite DB for each test."""
    storage_root = tmp_path / "storage"
    uploads = storage_root / "uploads"
    processed = storage_root / "processed"
    exports = storage_root / "exports"
    for directory in (uploads, processed, exports):
        directory.mkdir(parents=True)

    db_path = storage_root / "test.db"
    monkeypatch.setattr(settings, "storage_root", storage_root)
    monkeypatch.setattr(settings, "uploads_dir", uploads)
    monkeypatch.setattr(settings, "processed_dir", processed)
    monkeypatch.setattr(settings, "exports_dir", exports)
    monkeypatch.setattr(settings, "database_path", db_path)

    test_db = Database(db_path)
    db_module = importlib.import_module("app.db.database")
    monkeypatch.setattr(db_module, "database", test_db)
    for module in STORE_MODULES:
        monkeypatch.setattr(f"{module}.database", test_db)

    return storage_root


@pytest.fixture
async def api_client(
    test_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator:
    """HTTP client with fresh background workers on the current event loop."""
    from httpx import ASGITransport, AsyncClient

    import app.main as main_module
    import app.routers.process as process_router
    from app.main import app
    from app.services.ai.generation_queue import GenerationQueue
    from app.services.process_queue import ProcessQueue

    process_q = ProcessQueue()
    generation_q = GenerationQueue()
    monkeypatch.setattr("app.services.process_queue.process_queue", process_q)
    monkeypatch.setattr("app.services.ai.generation_queue.generation_queue", generation_q)
    monkeypatch.setattr(main_module, "process_queue", process_q)
    monkeypatch.setattr(main_module, "generation_queue", generation_q)
    monkeypatch.setattr(process_router, "process_queue", process_q)

    await generation_q.start()
    await process_q.start()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await process_q.stop()
    await generation_q.stop()


@pytest.fixture
def run_pipeline_sync(test_env: Path):
    """Run papercraft pipeline synchronously into isolated storage."""
    from app.services.papercraft_pipeline import run_pipeline

    def _run(
        fixture_name: str,
        *,
        project_id: str = "testproj001",
        project_name: str = "Test",
        settings_obj: ProjectSettings | None = None,
    ):
        source = FIXTURES_DIR / fixture_name
        if not source.exists():
            pytest.skip(f"Missing fixture {fixture_name}; run tests/fixtures/generate_fixtures.py")
        return run_pipeline(
            project_id=project_id,
            source_path=source,
            project_name=project_name,
            settings=settings_obj or ProjectSettings(
                paperSize=PaperSize.A4,
                difficulty=Difficulty.EASY,
                style=Style.LOW_POLY,
                targetHeightMm=80.0,
                addTabs=False,
                addNumbers=True,
                addFoldLines=True,
                addCutLines=True,
            ),
            source_original_path=source,
        )

    return _run


@pytest.fixture
def fast_layout(monkeypatch: pytest.MonkeyPatch):
    """Replace NFP nesting with a deterministic row layout in pipeline tests."""
    from tests.helpers.fast_layout import layout_pieces_row

    monkeypatch.setattr("app.services.layout_engine.layout_pieces", layout_pieces_row)
    monkeypatch.setattr("app.services.layout_repair.layout_pieces", layout_pieces_row)
    yield


async def wait_for_process_job(
    client,
    job_id: str,
    *,
    timeout_sec: float = 180.0,
    poll_interval_sec: float = 0.25,
) -> dict:
    """Poll process job until completed or failed."""
    import time

    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        response = await client.get(f"/api/process-jobs/{job_id}")
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in ("completed", "failed"):
            return payload
        await asyncio.sleep(poll_interval_sec)
    raise TimeoutError(f"Process job {job_id} did not finish within {timeout_sec}s")
