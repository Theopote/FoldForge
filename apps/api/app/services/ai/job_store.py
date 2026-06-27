"""In-memory generation job store (replace with Redis/DB in production)."""

from datetime import datetime, timezone

from app.schemas.generation_job import GenerationJob, JobStatus


class GenerationJobStore:
    """Thread-safe enough for asyncio single-worker MVP."""

    def __init__(self) -> None:
        self._jobs: dict[str, GenerationJob] = {}

    def create(self, job: GenerationJob) -> GenerationJob:
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        return self._jobs.get(job_id)

    def get_by_project(self, project_id: str) -> GenerationJob | None:
        for job in reversed(list(self._jobs.values())):
            if job.project_id == project_id:
                return job
        return None

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        enhanced_prompt: str | None = None,
    ) -> GenerationJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None

        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if enhanced_prompt is not None:
            job.enhanced_prompt = enhanced_prompt

        job.updated_at = datetime.now(timezone.utc)
        self._jobs[job_id] = job
        return job


generation_job_store = GenerationJobStore()
