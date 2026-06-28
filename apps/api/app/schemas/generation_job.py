"""Generation job status and storage for async AI queue."""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.job import JobStatus
from app.schemas.model import Style


class JobType(str, Enum):
    TEXT_TO_3D = "text_to_3d"
    IMAGE_TO_3D = "image_to_3d"


class GenerationJob(BaseModel):
    """Tracks async text/image → 3D generation work."""

    id: str
    project_id: str = Field(alias="projectId")
    job_type: JobType = Field(alias="jobType")
    status: JobStatus = JobStatus.QUEUED
    provider: str
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    prompt: str | None = None
    style: Style = Style.LOW_POLY
    image_path: str | None = None
    hint: str | None = None
    output_path: str
    enhanced_prompt: str | None = Field(alias="enhancedPrompt", default=None)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class GenerationJobResponse(BaseModel):
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    status: JobStatus
    provider: str
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    async_mode: bool = Field(alias="async", default=True)
    source_file_url: str | None = Field(alias="sourceFileUrl", default=None)
    source_image_url: str | None = Field(alias="sourceImageUrl", default=None)
    enhanced_prompt: str | None = Field(alias="enhancedPrompt", default=None)

    model_config = {"populate_by_name": True}
