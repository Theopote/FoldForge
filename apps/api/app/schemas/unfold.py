"""Schemas for unfold processing requests and responses."""

from pydantic import BaseModel, Field

from app.schemas.model import ProjectSettings, ProjectStatus


class ProcessModelRequest(BaseModel):
    project_id: str = Field(alias="projectId")
    settings: ProjectSettings

    model_config = {"populate_by_name": True}


class ProcessStats(BaseModel):
    faces: int = 0
    pieces: int = 0
    pages: int = 0
    difficulty_score: int = Field(alias="difficultyScore", default=0)

    model_config = {"populate_by_name": True}


class CraftabilityScore(BaseModel):
    score: int
    level: str
    warnings: list[str] = Field(default_factory=list)


class ProcessModelResponse(BaseModel):
    project_id: str = Field(alias="projectId")
    status: ProjectStatus
    processed_model_url: str | None = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: str | None = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: str | None = Field(alias="unfoldPdfUrl", default=None)
    stats: ProcessStats | None = None
    craftability: CraftabilityScore | None = None

    model_config = {"populate_by_name": True}
