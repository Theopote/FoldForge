"""In-memory project store for MVP (replace with database later)."""

from datetime import datetime, timezone

from app.schemas.model import Project, ProjectSettings, ProjectStatus, SourceType


class ProjectStore:
    """Simple dict-backed project repository."""

    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}

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
        self._projects[project_id] = project
        return project

    def get(self, project_id: str) -> Project | None:
        """Fetch a project by ID."""
        return self._projects.get(project_id)

    def update(self, project: Project) -> Project:
        """Update an existing project."""
        project.updated_at = datetime.now(timezone.utc)
        self._projects[project.id] = project
        return project

    def exists(self, project_id: str) -> bool:
        """Check whether a project exists."""
        return project_id in self._projects


project_store = ProjectStore()
