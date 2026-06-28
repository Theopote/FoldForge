"""SQLite database connection and schema initialization."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'upload_3d',
    status TEXT NOT NULL DEFAULT 'created',
    source_file_url TEXT,
    processed_model_url TEXT,
    unfold_pdf_url TEXT,
    unfold_svg_url TEXT,
    unfold_zip_url TEXT,
    settings_json TEXT NOT NULL DEFAULT '{}',
    stats_json TEXT,
    craftability_json TEXT,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_project_id
    ON generation_jobs(project_id);

CREATE INDEX IF NOT EXISTS idx_generation_jobs_status
    ON generation_jobs(status);

CREATE TABLE IF NOT EXISTS process_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    locked_by TEXT,
    locked_until TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX IF NOT EXISTS idx_process_jobs_project_id
    ON process_jobs(project_id);
"""

_PROCESS_JOB_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_process_jobs_status
    ON process_jobs(status);

CREATE INDEX IF NOT EXISTS idx_process_jobs_locked_until
    ON process_jobs(locked_until);
"""

_PROJECT_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_projects_status
    ON projects(status);

CREATE INDEX IF NOT EXISTS idx_projects_created_at
    ON projects(created_at);
"""

# Columns added after the initial MVP schema (id, data, created_at, updated_at).
_PROJECT_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("name", "TEXT NOT NULL DEFAULT ''"),
    ("source_type", "TEXT NOT NULL DEFAULT 'upload_3d'"),
    ("status", "TEXT NOT NULL DEFAULT 'created'"),
    ("source_file_url", "TEXT"),
    ("processed_model_url", "TEXT"),
    ("unfold_pdf_url", "TEXT"),
    ("unfold_svg_url", "TEXT"),
    ("unfold_zip_url", "TEXT"),
    ("settings_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("stats_json", "TEXT"),
    ("craftability_json", "TEXT"),
)

_PROCESS_JOB_COLUMN_MIGRATIONS: tuple[tuple[str, str], ...] = (
    ("locked_by", "TEXT"),
    ("locked_until", "TEXT"),
    ("attempts", "INTEGER NOT NULL DEFAULT 0"),
    ("last_error", "TEXT"),
)

_BUSY_TIMEOUT_MS = 5000


class _RWLock:
    """Reader-writer lock: concurrent reads, exclusive writes."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers = 0
        self._writers_waiting = 0
        self._writer_active = False

    def acquire_read(self) -> None:
        with self._cond:
            while self._writer_active or self._writers_waiting > 0:
                self._cond.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._cond:
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self) -> None:
        with self._cond:
            self._writers_waiting += 1
            try:
                while self._readers > 0 or self._writer_active:
                    self._cond.wait()
                self._writer_active = True
            finally:
                self._writers_waiting -= 1

    def release_write(self) -> None:
        with self._cond:
            self._writer_active = False
            self._cond.notify_all()


class Database:
    """Thread-safe SQLite access for FoldForge MVP persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = _RWLock()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        return conn

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        """Open a read connection. Multiple reads may run concurrently."""
        self._lock.acquire_read()
        try:
            conn = self._open_connection()
            try:
                yield conn
            finally:
                conn.close()
        finally:
            self._lock.release_read()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Open a read-write connection with exclusive access."""
        self._lock.acquire_write()
        try:
            conn = self._open_connection()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        finally:
            self._lock.release_write()

    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(_SCHEMA)
            self._migrate_projects_table(conn)
            self._migrate_process_jobs_table(conn)
            conn.executescript(_PROJECT_INDEXES)
            conn.executescript(_PROCESS_JOB_INDEXES)

    def _migrate_projects_table(self, conn: sqlite3.Connection) -> None:
        """Add indexed project columns and backfill from legacy JSON snapshots."""
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(projects)")}
        for column_name, column_def in _PROJECT_COLUMN_MIGRATIONS:
            if column_name not in existing:
                conn.execute(
                    f"ALTER TABLE projects ADD COLUMN {column_name} {column_def}"
                )

        rows = conn.execute(
            """
            SELECT id, data, name, source_type, status
            FROM projects
            WHERE data IS NOT NULL AND data != ''
            """
        ).fetchall()
        for row in rows:
            if row["name"]:
                continue
            try:
                payload = json.loads(row["data"])
            except json.JSONDecodeError:
                continue
            settings = payload.get("settings")
            stats = payload.get("stats")
            craftability = payload.get("craftability")
            conn.execute(
                """
                UPDATE projects SET
                    name = ?,
                    source_type = ?,
                    status = ?,
                    source_file_url = ?,
                    processed_model_url = ?,
                    unfold_pdf_url = ?,
                    unfold_svg_url = ?,
                    unfold_zip_url = ?,
                    settings_json = ?,
                    stats_json = ?,
                    craftability_json = ?
                WHERE id = ?
                """,
                (
                    payload.get("name") or "",
                    payload.get("sourceType") or "upload_3d",
                    payload.get("status") or "created",
                    payload.get("sourceFileUrl"),
                    payload.get("processedModelUrl"),
                    payload.get("unfoldPdfUrl"),
                    payload.get("unfoldSvgUrl"),
                    payload.get("unfoldZipUrl"),
                    json.dumps(settings if settings is not None else {}),
                    json.dumps(stats) if stats is not None else None,
                    json.dumps(craftability) if craftability is not None else None,
                    row["id"],
                ),
            )

    def _migrate_process_jobs_table(self, conn: sqlite3.Connection) -> None:
        """Add lease columns for multi-worker claim/recovery."""
        existing = {
            row["name"] for row in conn.execute("PRAGMA table_info(process_jobs)")
        }
        for column_name, column_def in _PROCESS_JOB_COLUMN_MIGRATIONS:
            if column_name not in existing:
                conn.execute(
                    f"ALTER TABLE process_jobs ADD COLUMN {column_name} {column_def}"
                )


database = Database(settings.database_path)
