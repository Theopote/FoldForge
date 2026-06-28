"""Background worker for async papercraft pipeline jobs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.schemas.job import JobStatus
from app.schemas.model import ProjectStatus
from app.schemas.stats import CraftabilityScore, ProcessStats
from app.services.papercraft_pipeline import run_pipeline
from app.services.pipeline_errors import UnfoldRepairError
from app.services.process_job_store import process_job_store
from app.services.project_store import project_store
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProcessQueue:
    """Single-worker asyncio queue for papercraft pipeline jobs."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._worker_task is None:
            return
        self._worker_task.cancel()
        try:
            await self._worker_task
        except asyncio.CancelledError:
            pass
        self._worker_task = None

    async def enqueue(self, job_id: str) -> None:
        await self._queue.put(job_id)

    async def recover_pending_jobs(self) -> None:
        pending = process_job_store.list_incomplete()
        if not pending:
            return

        logger.info("Recovering %d pending process job(s)", len(pending))
        for job in pending:
            if job.status == JobStatus.RUNNING:
                process_job_store.update(
                    job.id,
                    status=JobStatus.QUEUED,
                    message="Re-queued after server restart",
                )
            await self.enqueue(job.id)

    async def _worker_loop(self) -> None:
        while True:
            job_id = await self._queue.get()
            try:
                await self._process_job(job_id)
            except Exception as exc:
                logger.exception("Unhandled process job error for %s: %s", job_id, exc)
                process_job_store.update(
                    job_id,
                    status=JobStatus.FAILED,
                    error=str(exc),
                    message="Processing failed",
                )
            finally:
                self._queue.task_done()

    async def _process_job(self, job_id: str) -> None:
        job = process_job_store.get(job_id)
        if job is None:
            return

        project = project_store.get(job.project_id)
        if project is None:
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error="Project not found.",
                message="Processing failed",
            )
            return

        process_job_store.update(
            job_id,
            status=JobStatus.RUNNING,
            progress=5,
            message="Starting papercraft pipeline",
        )
        project.status = ProjectStatus.PROCESSING
        project.settings = job.settings
        project_store.update(project)

        def on_progress(progress: int, message: str) -> None:
            process_job_store.update(job_id, progress=progress, message=message)

        source_path = Path(job.source_path)
        try:
            result = await asyncio.to_thread(
                run_pipeline,
                project_id=job.project_id,
                source_path=source_path,
                project_name=job.project_name,
                settings=job.settings,
                source_original_path=source_path,
                on_progress=on_progress,
            )

            stats = ProcessStats(
                faces=result.face_count,
                pieces=len(result.pieces),
                pages=len(result.pages),
                difficultyScore=result.difficulty_score,
            )
            craftability = CraftabilityScore(
                score=result.craftability_score,
                level=result.craftability_level,
                warnings=result.warnings,
            )

            project.status = ProjectStatus.READY
            project.processed_model_url = result.processed_mesh_path
            project.unfold_svg_url = result.svg_path
            project.unfold_pdf_url = result.pdf_path
            project.unfold_zip_url = result.zip_path
            project.settings = job.settings
            project.stats = stats
            project.craftability = craftability
            project_store.update(project)

            process_job_store.update(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message="Complete",
                processed_model_url=result.processed_mesh_path,
                unfold_svg_url=result.svg_path,
                unfold_pdf_url=result.pdf_path,
                unfold_zip_url=result.zip_path,
                result_status=ProjectStatus.READY,
                stats=stats,
                craftability=craftability,
            )
        except UnfoldRepairError as exc:
            logger.warning("Process job %s failed repair: %s", job_id, exc)
            project.status = ProjectStatus.FAILED
            project_store.update(project)
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
                message="Unfold repair failed",
                result_status=ProjectStatus.FAILED,
            )
        except Exception as exc:
            logger.exception("Process job %s failed", job_id)
            project.status = ProjectStatus.FAILED
            project_store.update(project)
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
                message="Processing failed",
                result_status=ProjectStatus.FAILED,
            )


process_queue = ProcessQueue()
