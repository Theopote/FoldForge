"""Build API responses for generation job polling."""

from app.schemas.generation_job import GenerationJob, GenerationJobResponse, JobStatus
from app.services.project_store import project_store


def build_generation_job_response(job: GenerationJob) -> GenerationJobResponse:
    """Map a stored job and project URLs into the poll response shape."""
    project = project_store.get(job.project_id)
    source_file_url = project.source_file_url if project else None
    source_image_url = project.source_image_url if project else None

    return GenerationJobResponse(
        jobId=job.id,
        projectId=job.project_id,
        status=job.status,
        provider=job.provider,
        progress=job.progress,
        message=job.message,
        error=job.error,
        async_mode=True,
        sourceFileUrl=source_file_url if job.status == JobStatus.COMPLETED else None,
        sourceImageUrl=source_image_url,
        enhancedPrompt=job.enhanced_prompt,
    )
