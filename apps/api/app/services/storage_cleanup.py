"""Background cleanup for orphaned files under storage/."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.db.database import database
from app.schemas.job import JobStatus
from app.utils.file_utils import resolve_storage_path
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

_INCOMPLETE_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)
_PROJECT_URL_COLUMNS = (
    "source_file_url",
    "processed_model_url",
    "unfold_pdf_url",
    "unfold_svg_url",
    "unfold_zip_url",
)
_STORAGE_SUBDIR_NAMES = ("uploads_dir", "processed_dir", "exports_dir")


@dataclass(frozen=True)
class StorageCleanupResult:
    scanned: int = 0
    deleted: int = 0
    protected: int = 0
    skipped_young: int = 0


class StorageCleanupTask:
    """Periodic task that removes unreferenced storage files past TTL."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not settings.storage_cleanup_enabled:
            logger.info("Storage cleanup disabled")
            return

        result = await asyncio.to_thread(run_storage_cleanup)
        if result.deleted:
            logger.info(
                "Storage cleanup removed %d orphaned file(s) on startup",
                result.deleted,
            )

        self._task = asyncio.create_task(self._loop())
        logger.info(
            "Storage cleanup scheduled every %.0fs (TTL %d days)",
            settings.storage_cleanup_interval_sec,
            settings.storage_file_ttl_days,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(settings.storage_cleanup_interval_sec)
            try:
                result = await asyncio.to_thread(run_storage_cleanup)
                if result.deleted:
                    logger.info(
                        "Storage cleanup removed %d orphaned file(s)",
                        result.deleted,
                    )
            except Exception:
                logger.exception("Storage cleanup failed")


def run_storage_cleanup(
    *,
    ttl_days: int | None = None,
    now: float | None = None,
) -> StorageCleanupResult:
    """Delete unreferenced files in uploads/processed/exports older than TTL."""
    ttl = ttl_days if ttl_days is not None else settings.storage_file_ttl_days
    if ttl < 0:
        raise ValueError("storage_file_ttl_days must be non-negative")

    current_time = now if now is not None else time.time()
    cutoff = current_time - ttl * 86400
    storage_root = settings.storage_root.resolve()
    referenced = _collect_referenced_paths(storage_root)

    scanned = 0
    deleted = 0
    protected = 0
    skipped_young = 0

    for subdir_name in _STORAGE_SUBDIR_NAMES:
        directory = getattr(settings, subdir_name)
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if not path.is_file() or path.name == ".gitkeep":
                continue

            scanned += 1
            resolved = path.resolve()

            if resolved in referenced:
                protected += 1
                continue

            if path.stat().st_mtime > cutoff:
                skipped_young += 1
                continue

            path.unlink(missing_ok=True)
            deleted += 1
            logger.debug("Removed orphaned storage file %s", resolved)

    return StorageCleanupResult(
        scanned=scanned,
        deleted=deleted,
        protected=protected,
        skipped_young=skipped_young,
    )


def _collect_referenced_paths(storage_root: Path) -> set[Path]:
    referenced: set[Path] = set()

    with database.read_connection() as conn:
        project_rows = conn.execute(
            f"""
            SELECT {", ".join(_PROJECT_URL_COLUMNS)}, data
            FROM projects
            """
        ).fetchall()
        for row in project_rows:
            for column in _PROJECT_URL_COLUMNS:
                _register_path(referenced, row[column], storage_root)
            _register_json_paths(
                referenced,
                row["data"],
                storage_root,
                ("sourceImageUrl", "sourceFileUrl", "processedModelUrl",
                 "unfoldPdfUrl", "unfoldSvgUrl", "unfoldZipUrl"),
            )

        incomplete_placeholders = ", ".join("?" for _ in _INCOMPLETE_STATUSES)
        process_rows = conn.execute(
            f"""
            SELECT data FROM process_jobs
            WHERE status IN ({incomplete_placeholders})
            """,
            _INCOMPLETE_STATUSES,
        ).fetchall()
        for row in process_rows:
            _register_json_paths(
                referenced,
                row["data"],
                storage_root,
                (
                    "sourcePath",
                    "processedModelUrl",
                    "unfoldPdfUrl",
                    "unfoldSvgUrl",
                    "unfoldZipUrl",
                ),
            )

        generation_rows = conn.execute(
            f"""
            SELECT data FROM generation_jobs
            WHERE status IN ({incomplete_placeholders})
            """,
            _INCOMPLETE_STATUSES,
        ).fetchall()
        for row in generation_rows:
            _register_json_paths(
                referenced,
                row["data"],
                storage_root,
                ("output_path", "outputPath", "image_path", "imagePath"),
            )

    return referenced


def _register_json_paths(
    referenced: set[Path],
    payload: str | None,
    storage_root: Path,
    keys: tuple[str, ...],
) -> None:
    if not payload:
        return
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return
    for key in keys:
        value = data.get(key)
        if isinstance(value, str):
            _register_path(referenced, value, storage_root)


def _register_path(
    referenced: set[Path],
    value: str | None,
    storage_root: Path,
) -> None:
    if not value:
        return

    if value.startswith("/storage/"):
        try:
            referenced.add(resolve_storage_path(value).resolve())
        except ValueError:
            return
        return

    path = Path(value)
    if not path.is_absolute():
        return

    try:
        resolved = path.resolve()
    except OSError:
        return

    if str(resolved).startswith(str(storage_root)):
        referenced.add(resolved)


storage_cleanup_task = StorageCleanupTask()
