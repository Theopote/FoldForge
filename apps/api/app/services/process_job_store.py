"""SQLite-backed papercraft process job store."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.database import database
from app.schemas.job import JobStatus
from app.schemas.process_job import ProcessJob


class ProcessJobStore:
    """Persistent store for async papercraft pipeline jobs."""

    def create(self, job: ProcessJob) -> ProcessJob:
        self._save(job)
        return job

    def get(self, job_id: str) -> ProcessJob | None:
        with database.connection() as conn:
            row = conn.execute(
                "SELECT data FROM process_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return ProcessJob.model_validate(json.loads(row["data"]))

    def get_by_project(self, project_id: str) -> ProcessJob | None:
        with database.connection() as conn:
            row = conn.execute(
                """
                SELECT data FROM process_jobs
                WHERE project_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return ProcessJob.model_validate(json.loads(row["data"]))

    def list_incomplete(self) -> list[ProcessJob]:
        placeholders = ", ".join("?" for _ in _INCOMPLETE_STATUSES)
        with database.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT data FROM process_jobs
                WHERE status IN ({placeholders})
                ORDER BY created_at ASC
                """,
                _INCOMPLETE_STATUSES,
            ).fetchall()
        return [ProcessJob.model_validate(json.loads(row["data"])) for row in rows]

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        processed_model_url: str | None = None,
        unfold_svg_url: str | None = None,
        unfold_pdf_url: str | None = None,
        unfold_zip_url: str | None = None,
        result_status=None,
        stats=None,
        craftability=None,
    ) -> ProcessJob | None:
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
        if processed_model_url is not None:
            job.processed_model_url = processed_model_url
        if unfold_svg_url is not None:
            job.unfold_svg_url = unfold_svg_url
        if unfold_pdf_url is not None:
            job.unfold_pdf_url = unfold_pdf_url
        if unfold_zip_url is not None:
            job.unfold_zip_url = unfold_zip_url
        if result_status is not None:
            job.result_status = result_status
        if stats is not None:
            job.stats = stats
        if craftability is not None:
            job.craftability = craftability

        job.updated_at = datetime.now(timezone.utc)
        self._save(job)
        return job

    def _save(self, job: ProcessJob) -> None:
        payload = json.dumps(job.model_dump(mode="json", by_alias=True))
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO process_jobs (
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

process_job_store = ProcessJobStore()
