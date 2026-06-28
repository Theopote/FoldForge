"""Background worker for async AI model generation."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.schemas.generation_job import JobStatus, JobType
from app.schemas.model import ProjectStatus
from app.services.ai.job_store import generation_job_store
from app.services.ai.registry import get_provider_by_name
from app.services.project_store import project_store
from app.utils.file_utils import build_storage_url
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class GenerationQueue:
    """Single-worker asyncio queue for production AI generation jobs."""

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
        """Re-queue jobs that were interrupted by a server restart."""
        pending = generation_job_store.list_incomplete()
        if not pending:
            return

        logger.info("Recovering %d pending generation job(s)", len(pending))
        for job in pending:
            if job.status == JobStatus.RUNNING:
                generation_job_store.update(
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
                logger.exception("Unhandled job error for %s: %s", job_id, exc)
                generation_job_store.update(
                    job_id,
                    status=JobStatus.FAILED,
                    error=str(exc),
                    message="Generation failed",
                )
            finally:
                self._queue.task_done()

    async def _process_job(self, job_id: str) -> None:
        job = generation_job_store.get(job_id)
        if job is None:
            return

        generation_job_store.update(
            job_id,
            status=JobStatus.RUNNING,
            progress=5,
            message="Starting generation",
        )

        project = project_store.get(job.project_id)
        if project:
            project.status = ProjectStatus.PROCESSING
            project_store.update(project)

        provider = get_provider_by_name(job.provider)

        def on_progress(progress: int, message: str) -> None:
            generation_job_store.update(job_id, progress=progress, message=message)

        output_path = Path(job.output_path)
        try:
            if job.job_type == JobType.TEXT_TO_3D:
                result = await provider.generate_from_text(
                    job.prompt or "",
                    job.style,
                    output_path,
                    on_progress=on_progress,
                )
            else:
                if not job.image_path:
                    raise RuntimeError("Image job missing image_path")
                result = await provider.generate_from_image(
                    Path(job.image_path),
                    job.style,
                    output_path,
                    hint=job.hint,
                    on_progress=on_progress,
                )

            if not result.model_path.exists():
                raise RuntimeError("Provider finished but model file is missing")

            source_url = build_storage_url(Path("uploads") / output_path.name)
            project = project_store.get(job.project_id)
            if project:
                project.source_file_url = source_url
                project.status = ProjectStatus.UPLOADED
                project.ai_provider = result.provider
                project.enhanced_prompt = result.enhanced_prompt
                project_store.update(project)

            generation_job_store.update(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                message="Complete",
                enhanced_prompt=result.enhanced_prompt,
            )
        except Exception as exc:
            logger.warning("Generation job %s failed: %s", job_id, exc)
            generation_job_store.update(
                job_id,
                status=JobStatus.FAILED,
                error=str(exc),
                message="Generation failed",
            )
            project = project_store.get(job.project_id)
            if project:
                project.status = ProjectStatus.FAILED
                project_store.update(project)


generation_queue = GenerationQueue()
