"""SQLite-backed project store."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.database import database
from app.schemas.model import Project, ProjectSettings, ProjectStatus, SourceType


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
                "SELECT data FROM projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        if row is None:
            return None
        return Project.model_validate(json.loads(row["data"]))

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
        with database.connection() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (
                    project.id,
                    payload,
                    project.created_at.isoformat(),
                    project.updated_at.isoformat(),
                ),
            )


project_store = ProjectStore()
