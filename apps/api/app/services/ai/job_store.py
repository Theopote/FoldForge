"""SQLite-backed generation job store."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.database import database
from app.schemas.generation_job import GenerationJob, JobStatus


class GenerationJobStore:
    """Persistent store for async AI generation jobs."""

    def create(self, job: GenerationJob) -> GenerationJob:
        self._save(job)
        return job

    def get(self, job_id: str) -> GenerationJob | None:
        with database.connection() as conn:
            row = conn.execute(
                "SELECT data FROM generation_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return GenerationJob.model_validate(json.loads(row["data"]))

    def get_by_project(self, project_id: str) -> GenerationJob | None:
        with database.connection() as conn:
            row = conn.execute(
                """
                SELECT data FROM generation_jobs
                WHERE project_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return GenerationJob.model_validate(json.loads(row["data"]))

    def list_incomplete(self) -> list[GenerationJob]:
        """Return queued or running jobs (for restart recovery)."""
        placeholders = ", ".join("?" for _ in _INCOMPLETE_STATUSES)
        with database.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT data FROM generation_jobs
                WHERE status IN ({placeholders})
                ORDER BY created_at ASC
                """,
                _INCOMPLETE_STATUSES,
            ).fetchall()
        return [GenerationJob.model_validate(json.loads(row["data"])) for row in rows]

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
        job = self.get(job_id)
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
        self._save(job)
        return job

    def _save(self, job: GenerationJob) -> None:
        payload = json.dumps(job.model_dump(mode="json", by_alias=True))
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO generation_jobs (
                    id, project_id, data, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    job.id,
                    job.project_id,
                    payload,
                    job.status.value,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )


_INCOMPLETE_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)

generation_job_store = GenerationJobStore()
