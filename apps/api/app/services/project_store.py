"""SQLite-backed project store."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.database import database
from app.schemas.model import Project, ProjectSettings, ProjectStatus, SourceType

_PROJECT_COLUMNS = """
    id, name, source_type, status,
    source_file_url, processed_model_url,
    unfold_pdf_url, unfold_svg_url, unfold_zip_url,
    settings_json, stats_json, craftability_json,
    data, created_at, updated_at
"""

_SNAPSHOT_ONLY_FIELDS = (
    "sourcePrompt",
    "sourceImageUrl",
    "aiProvider",
    "enhancedPrompt",
)


class ProjectStore:
    """Persistent project repository backed by SQLite."""

    def create(
        self,
        project_id: str,
        name: str,
        source_type: SourceType = SourceType.UPLOAD_3D,
        source_file_url: str | None = None,
        settings: ProjectSettings | None = None,
        status: ProjectStatus = ProjectStatus.CREATED,
        source_prompt: str | None = None,
        source_image_url: str | None = None,
        ai_provider: str | None = None,
        enhanced_prompt: str | None = None,
    ) -> Project:
        """Create and persist a new project."""
        now = datetime.now(timezone.utc)
        project = Project(
            id=project_id,
            name=name,
            sourceType=source_type,
            sourceFileUrl=source_file_url,
            status=status,
            settings=settings or ProjectSettings(),
            sourcePrompt=source_prompt,
            sourceImageUrl=source_image_url,
            aiProvider=ai_provider,
            enhancedPrompt=enhanced_prompt,
            createdAt=now,
            updatedAt=now,
        )
        self._save(project)
        return project

    def get(self, project_id: str) -> Project | None:
        """Fetch a project by ID."""
        with database.connection() as conn:
            row = conn.execute(
                f"SELECT {_PROJECT_COLUMNS} FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_project(row)

    def update(self, project: Project) -> Project:
        """Update an existing project."""
        project.updated_at = datetime.now(timezone.utc)
        self._save(project)
        return project

    def exists(self, project_id: str) -> bool:
        """Check whether a project exists."""
        with database.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        return row is not None

    def _save(self, project: Project) -> None:
        payload = json.dumps(project.model_dump(mode="json", by_alias=True))
        settings_json = json.dumps(
            project.settings.model_dump(mode="json", by_alias=True)
        )
        stats_json = (
            json.dumps(project.stats.model_dump(mode="json", by_alias=True))
            if project.stats is not None
            else None
        )
        craftability_json = (
            json.dumps(project.craftability.model_dump(mode="json", by_alias=True))
            if project.craftability is not None
            else None
        )
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, name, source_type, status,
                    source_file_url, processed_model_url,
                    unfold_pdf_url, unfold_svg_url, unfold_zip_url,
                    settings_json, stats_json, craftability_json,
                    data, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    source_type = excluded.source_type,
                    status = excluded.status,
                    source_file_url = excluded.source_file_url,
                    processed_model_url = excluded.processed_model_url,
                    unfold_pdf_url = excluded.unfold_pdf_url,
                    unfold_svg_url = excluded.unfold_svg_url,
                    unfold_zip_url = excluded.unfold_zip_url,
                    settings_json = excluded.settings_json,
                    stats_json = excluded.stats_json,
                    craftability_json = excluded.craftability_json,
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (
                    project.id,
                    project.name,
                    project.source_type.value,
                    project.status.value,
                    project.source_file_url,
                    project.processed_model_url,
                    project.unfold_pdf_url,
                    project.unfold_svg_url,
                    project.unfold_zip_url,
                    settings_json,
                    stats_json,
                    craftability_json,
                    payload,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )


def _row_to_project(row) -> Project:
    """Build a Project from indexed columns, with snapshot-only field overlay."""
    if not row["name"]:
        return Project.model_validate(json.loads(row["data"]))

    payload: dict = {
        "id": row["id"],
        "name": row["name"],
        "sourceType": row["source_type"],
        "sourceFileUrl": row["source_file_url"],
        "processedModelUrl": row["processed_model_url"],
        "unfoldPdfUrl": row["unfold_pdf_url"],
        "unfoldSvgUrl": row["unfold_svg_url"],
        "unfoldZipUrl": row["unfold_zip_url"],
        "status": row["status"],
        "settings": json.loads(row["settings_json"] or "{}"),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }
    if row["stats_json"]:
        payload["stats"] = json.loads(row["stats_json"])
    if row["craftability_json"]:
        payload["craftability"] = json.loads(row["craftability_json"])

    if row["data"]:
        snapshot = json.loads(row["data"])
        for field in _SNAPSHOT_ONLY_FIELDS:
            if field in snapshot and snapshot[field] is not None:
                payload[field] = snapshot[field]

    return Project.model_validate(payload)


project_store = ProjectStore()
