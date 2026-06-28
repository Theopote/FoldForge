"""Unified async job polling (AI generation + papercraft processing)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.job import JobKind, JobStatus
from app.schemas.stats import CraftabilityScore, ProcessStats
from app.services.ai.job_store import generation_job_store
from app.services.ai.job_response import build_generation_job_response
from app.services.process_job_store import process_job_store
from app.services.process_job_response import build_process_job_response

router = APIRouter()


class UnifiedJobResponse(BaseModel):
    job_id: str = Field(alias="jobId")
    project_id: str = Field(alias="projectId")
    kind: JobKind
    status: JobStatus
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    async_mode: bool = Field(alias="async", default=True)
    provider: str | None = None
    source_file_url: str | None = Field(alias="sourceFileUrl", default=None)
    source_image_url: str | None = Field(alias="sourceImageUrl", default=None)
    enhanced_prompt: str | None = Field(alias="enhancedPrompt", default=None)
    processed_model_url: str | None = Field(alias="processedModelUrl", default=None)
    unfold_svg_url: str | None = Field(alias="unfoldSvgUrl", default=None)
    unfold_pdf_url: str | None = Field(alias="unfoldPdfUrl", default=None)
    unfold_zip_url: str | None = Field(alias="unfoldZipUrl", default=None)
    result_status: str | None = Field(alias="resultStatus", default=None)
    stats: ProcessStats | None = None
    craftability: CraftabilityScore | None = None

    model_config = {"populate_by_name": True}


@router.get("/jobs/{job_id}", response_model=UnifiedJobResponse)
async def get_job(job_id: str) -> UnifiedJobResponse:
    """Poll any async job by ID (AI generation or papercraft processing)."""
    process_job = process_job_store.get(job_id)
    if process_job is not None:
        response = build_process_job_response(process_job)
        return UnifiedJobResponse(
            jobId=response.job_id,
            projectId=response.project_id,
            kind=JobKind.PAPERCRAFT_PROCESS,
            status=response.status,
            progress=response.progress,
            message=response.message,
            error=response.error,
            async_mode=True,
            processedModelUrl=response.processed_model_url,
            unfoldSvgUrl=response.unfold_svg_url,
            unfoldPdfUrl=response.unfold_pdf_url,
            unfoldZipUrl=response.unfold_zip_url,
            resultStatus=response.result_status.value if response.result_status else None,
            stats=response.stats,
            craftability=response.craftability,
        )

    generation_job = generation_job_store.get(job_id)
    if generation_job is not None:
        response = build_generation_job_response(generation_job)
        return UnifiedJobResponse(
            jobId=response.job_id,
            projectId=response.project_id,
            kind=JobKind.AI_GENERATION,
            status=response.status,
            progress=response.progress,
            message=response.message,
            error=response.error,
            async_mode=True,
            provider=response.provider,
            sourceFileUrl=response.source_file_url,
            sourceImageUrl=response.source_image_url,
            enhancedPrompt=response.enhanced_prompt,
        )

    raise HTTPException(status_code=404, detail="Job not found.")
