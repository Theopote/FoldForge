"""SQLite-backed papercraft process job store."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.db.database import database
from app.schemas.job import JobStatus
from app.schemas.process_job import ProcessJob

_INCOMPLETE_STATUSES = (JobStatus.QUEUED.value, JobStatus.RUNNING.value)


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

    def list_claimable(self) -> list[ProcessJob]:
        """Return queued/running jobs with no active lease (for recovery)."""
        now = _utc_now_iso()
        placeholders = ", ".join("?" for _ in _INCOMPLETE_STATUSES)
        with database.connection() as conn:
            rows = conn.execute(
                f"""
                SELECT data FROM process_jobs
                WHERE status IN ({placeholders})
                  AND (locked_until IS NULL OR locked_until <= ?)
                ORDER BY created_at ASC
                """,
                (*_INCOMPLETE_STATUSES, now),
            ).fetchall()
        return [ProcessJob.model_validate(json.loads(row["data"])) for row in rows]

    def count_queued(self) -> int:
        """Count jobs waiting for a worker (queued with no active lease)."""
        now = _utc_now_iso()
        with database.connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM process_jobs
                WHERE status = ?
                  AND (locked_until IS NULL OR locked_until <= ?)
                """,
                (JobStatus.QUEUED.value, now),
            ).fetchone()
        return int(row["count"])

    def try_acquire_lock(
        self,
        job_id: str,
        worker_id: str,
        lease_sec: int,
    ) -> ProcessJob | None:
        """Atomically claim a job for processing. Returns None if already locked."""
        now = datetime.now(timezone.utc)
        locked_until = now + timedelta(seconds=lease_sec)
        with database.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE process_jobs
                SET
                    locked_by = ?,
                    locked_until = ?,
                    status = ?,
                    attempts = attempts + 1,
                    updated_at = ?
                WHERE id = ?
                  AND status IN (?, ?)
                  AND (locked_until IS NULL OR locked_until <= ?)
                """,
                (
                    worker_id,
                    locked_until.isoformat(),
                    JobStatus.RUNNING.value,
                    now.isoformat(),
                    job_id,
                    JobStatus.QUEUED.value,
                    JobStatus.RUNNING.value,
                    now.isoformat(),
                ),
            )
            if cursor.rowcount != 1:
                return None
            row = conn.execute(
                "SELECT data, attempts FROM process_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        job = ProcessJob.model_validate(json.loads(row["data"]))
        job.locked_by = worker_id
        job.locked_until = locked_until
        job.status = JobStatus.RUNNING
        job.attempts = int(row["attempts"])
        job.updated_at = now
        self._save(job)
        return job

    def renew_lock(self, job_id: str, worker_id: str, lease_sec: int) -> bool:
        """Extend the lease while a worker is still processing."""
        now = datetime.now(timezone.utc)
        locked_until = now + timedelta(seconds=lease_sec)
        with database.connection() as conn:
            cursor = conn.execute(
                """
                UPDATE process_jobs
                SET locked_until = ?, updated_at = ?
                WHERE id = ? AND locked_by = ?
                """,
                (locked_until.isoformat(), now.isoformat(), job_id, worker_id),
            )
            if cursor.rowcount != 1:
                return False

        job = self.get(job_id)
        if job is None:
            return False

        job.locked_until = locked_until
        job.updated_at = now
        self._save(job)
        return True

    def release_lock(self, job_id: str, worker_id: str) -> None:
        """Clear the lease after processing finishes."""
        now = datetime.now(timezone.utc)
        with database.connection() as conn:
            conn.execute(
                """
                UPDATE process_jobs
                SET locked_by = NULL, locked_until = NULL, updated_at = ?
                WHERE id = ? AND locked_by = ?
                """,
                (now.isoformat(), job_id, worker_id),
            )

        job = self.get(job_id)
        if job is None:
            return

        job.locked_by = None
        job.locked_until = None
        job.updated_at = now
        self._save(job)

    def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
        error: str | None = None,
        last_error: str | None = None,
        processed_model_url: str | None = None,
        unfold_svg_url: str | None = None,
        unfold_pdf_url: str | None = None,
        unfold_zip_url: str | None = None,
        result_status=None,
        stats=None,
        craftability=None,
        export_blocked: bool | None = None,
        has_unfold_overlap: bool | None = None,
        cancel_requested: bool | None = None,
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
        if last_error is not None:
            job.last_error = last_error
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
        if export_blocked is not None:
            job.export_blocked = export_blocked
        if has_unfold_overlap is not None:
            job.has_unfold_overlap = has_unfold_overlap
        if cancel_requested is not None:
            job.cancel_requested = cancel_requested

        job.updated_at = datetime.now(timezone.utc)
        self._save(job)
        return job

    def is_cancel_requested(self, job_id: str) -> bool:
        job = self.get(job_id)
        return bool(job and job.cancel_requested)

    def cancel(self, job_id: str) -> ProcessJob | None:
        """Cancel a queued job immediately or request stop for a running job."""
        job = self.get(job_id)
        if job is None:
            return None

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return job

        if job.status == JobStatus.QUEUED:
            return self.update(
                job_id,
                status=JobStatus.CANCELLED,
                message="Cancelled",
                cancel_requested=False,
            )

        return self.update(
            job_id,
            cancel_requested=True,
            message="Cancellation requested",
        )

    def _save(self, job: ProcessJob) -> None:
        payload = json.dumps(job.model_dump(mode="json", by_alias=True))
        locked_until = (
            job.locked_until.isoformat() if job.locked_until is not None else None
        )
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO process_jobs (
                    id, project_id, data, status,
                    locked_by, locked_until, attempts, last_error,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    status = excluded.status,
                    locked_by = excluded.locked_by,
                    locked_until = excluded.locked_until,
                    attempts = excluded.attempts,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at
                """,
                (
                    job.id,
                    job.project_id,
                    payload,
                    job.status.value,
                    job.locked_by,
                    locked_until,
                    job.attempts,
                    job.last_error,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


process_job_store = ProcessJobStore()
