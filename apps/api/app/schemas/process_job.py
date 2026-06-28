"""Async papercraft processing job schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.job import JobStatus
from app.schemas.model import ProjectSettings, ProjectStatus
from app.schemas.stats import CraftabilityScore, ProcessStats


class ProcessJob(BaseModel):
    """Tracks async papercraft pipeline work for a project."""

    id: str
    project_id: str = Field(alias="projectId")
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    settings: ProjectSettings
    project_name: str = Field(alias="projectName")
    source_path: str = Field(alias="sourcePath")
    processed_model_url: str | None = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: str | None = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: str | None = Field(alias="unfoldPdfUrl", default=None)
    unfold_zip_url: str | None = Field(alias="unfoldZipUrl", default=None)
    result_status: ProjectStatus | None = Field(alias="resultStatus", default=None)
    stats: ProcessStats | None = None
    craftability: CraftabilityScore | None = None
    export_blocked: bool = Field(alias="exportBlocked", default=False)
    has_unfold_overlap: bool = Field(alias="hasUnfoldOverlap", default=False)
    cancel_requested: bool = Field(alias="cancelRequested", default=False)
    locked_by: str | None = Field(alias="lockedBy", default=None)
    locked_until: datetime | None = Field(alias="lockedUntil", default=None)
    attempts: int = 0
    last_error: str | None = Field(alias="lastError", default=None)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class ProcessJobResponse(BaseModel):
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    status: JobStatus
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    async_mode: bool = Field(alias="async", default=True)
    processed_model_url: str | None = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: str | None = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: str | None = Field(alias="unfoldPdfUrl", default=None)
    unfold_zip_url: str | None = Field(alias="unfoldZipUrl", default=None)
    result_status: ProjectStatus | None = Field(alias="resultStatus", default=None)
    stats: ProcessStats | None = None
    craftability: CraftabilityScore | None = None
    export_blocked: bool = Field(alias="exportBlocked", default=False)
    has_unfold_overlap: bool = Field(alias="hasUnfoldOverlap", default=False)
    cancel_requested: bool = Field(alias="cancelRequested", default=False)

    model_config = {"populate_by_name": True}
