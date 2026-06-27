"""Schemas for unfold processing requests and responses."""

from pydantic import BaseModel, Field

from app.schemas.model import ProjectSettings, ProjectStatus
from app.schemas.stats import CraftabilityScore, ProcessStats


class ProcessModelRequest(BaseModel):
    project_id: str = Field(alias="projectId")
    settings: ProjectSettings

    model_config = {"populate_by_name": True}


class ProcessModelResponse(BaseModel):
    project_id: str = Field(alias="projectId")
    status: ProjectStatus
    processed_model_url: str | None = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: str | None = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: str | None = Field(alias="unfoldPdfUrl", default=None)
    unfold_zip_url: str | None = Field(alias="unfoldZipUrl", default=None)
    stats: ProcessStats | None = None
    craftability: CraftabilityScore | None = None

    model_config = {"populate_by_name": True}
