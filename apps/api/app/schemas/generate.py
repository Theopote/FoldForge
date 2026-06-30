"""Schemas for AI text/image model generation."""

from pydantic import BaseModel, Field

from app.schemas.job import JobStatus
from app.schemas.model import ProjectStatus, SourceType, Style


class GenerateFromTextRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    style: Style = Style.LOW_POLY
    name: str | None = Field(default=None, max_length=80)

    model_config = {"populate_by_name": True}


class GenerateModelResponse(BaseModel):
    project_id: str = Field(alias="projectId")
    source_type: SourceType = Field(alias="sourceType")
    source_file_url: str | None = Field(alias="sourceFileUrl", default=None)
    source_prompt: str | None = Field(alias="sourcePrompt", default=None)
    source_image_url: str | None = Field(alias="sourceImageUrl", default=None)
    ai_provider: str = Field(alias="aiProvider")
    enhanced_prompt: str | None = Field(alias="enhancedPrompt", default=None)
    status: ProjectStatus
    job_id: str | None = Field(alias="jobId", default=None)
    async_mode: bool = Field(alias="async", default=False)
    job_status: JobStatus | None = Field(alias="jobStatus", default=None)
    progress: int = 0
    message: str | None = None

    model_config = {"populate_by_name": True}


class AiProviderInfo(BaseModel):
    name: str
    active: bool
    available: bool
    configured: bool = True
    text: bool = True
    image: bool = True
    reason: str | None = None
    async_mode: bool = Field(alias="async", default=False)

    model_config = {"populate_by_name": True}
