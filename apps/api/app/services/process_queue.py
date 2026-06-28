"""Background worker for async papercraft pipeline jobs."""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from pathlib import Path

from app.config import settings
from app.schemas.job import JobStatus
from app.schemas.model import ProjectStatus
from app.schemas.stats import CraftabilityScore, ProcessStats
from app.services.papercraft_pipeline import run_pipeline
from app.services.pipeline_errors import JobCancelledError, LayoutFitError, UnfoldRepairError
from app.services.process_job_store import process_job_store
from app.services.project_store import project_store
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def _default_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class ProcessQueue:
    """Single-worker asyncio queue for papercraft pipeline jobs.

    Jobs are claimed via DB lease columns so multiple instances can share
    the same SQLite store without double-processing the same job.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._worker_id = settings.process_worker_id or _default_worker_id()
        self._lease_sec = settings.process_job_lease_sec

    @property
    def worker_id(self) -> str:
        return self._worker_id

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Process worker started as %s", self._worker_id)

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
        claimable = process_job_store.list_claimable()
        if not claimable:
            return

        logger.info("Recovering %d claimable process job(s)", len(claimable))
        for job in claimable:
            if job.status == JobStatus.RUNNING:
                process_job_store.update(
                    job.id,
                    status=JobStatus.QUEUED,
                    message="Re-queued after lease expiry or restart",
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
                    last_error=str(exc),
                    message="Processing failed",
                )
                process_job_store.release_lock(job_id, self._worker_id)
            finally:
                self._queue.task_done()

    async def _process_job(self, job_id: str) -> None:
        job = process_job_store.get(job_id)
        if job is None:
            return
        if job.status == JobStatus.CANCELLED:
            return

        job = process_job_store.try_acquire_lock(
            job_id,
            self._worker_id,
            self._lease_sec,
        )
        if job is None:
            logger.debug("Process job %s skipped; already locked elsewhere", job_id)
            return

        project = project_store.get(job.project_id)
        if project is None:
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error="Project not found.",
                last_error="Project not found.",
                message="Processing failed",
            )
            process_job_store.release_lock(job_id, self._worker_id)
            return

        process_job_store.update(
            job_id,
            progress=5,
            message="Starting papercraft pipeline",
        )
        project.status = ProjectStatus.PROCESSING
        project.settings = job.settings
        project_store.update(project)

        def on_progress(progress: int, message: str) -> None:
            if process_job_store.update_progress_and_renew_lock(
                job_id,
                self._worker_id,
                self._lease_sec,
                progress=progress,
                message=message,
            ):
                raise JobCancelledError("Processing cancelled.")

        def cancel_check() -> bool:
            return process_job_store.is_cancel_requested(job_id)

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
                cancel_check=cancel_check,
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
                export_blocked=result.export_blocked,
                has_unfold_overlap=result.has_unfold_overlap,
            )
        except JobCancelledError:
            logger.info("Process job %s cancelled", job_id)
            project.status = ProjectStatus.UPLOADED
            project_store.update(project)
            process_job_store.update(
                job_id,
                status=JobStatus.CANCELLED,
                message="Cancelled",
                cancel_requested=False,
            )
        except LayoutFitError as exc:
            logger.warning("Process job %s layout fit failed: %s", job_id, exc)
            project.status = ProjectStatus.FAILED
            project_store.update(project)
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
                last_error=str(exc),
                message="Layout fit failed",
                result_status=ProjectStatus.FAILED,
            )
        except UnfoldRepairError as exc:
            logger.warning("Process job %s failed repair: %s", job_id, exc)
            project.status = ProjectStatus.FAILED
            project_store.update(project)
            process_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
                last_error=str(exc),
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
                last_error=str(exc),
                message="Processing failed",
                result_status=ProjectStatus.FAILED,
            )
        finally:
            process_job_store.release_lock(job_id, self._worker_id)


process_queue = ProcessQueue()
