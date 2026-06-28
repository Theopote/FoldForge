"""Model processing router."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.generation_job import GenerationJobResponse
from app.schemas.job import JobStatus
from app.schemas.model import ProjectStatus
from app.schemas.process_job import ProcessJob, ProcessJobResponse
from app.schemas.unfold import ProcessModelRequest
from app.services.ai.job_response import build_generation_job_response
from app.services.ai.job_store import generation_job_store
from app.services.process_job_response import build_process_job_response
from app.services.process_job_store import process_job_store
from app.services.process_queue import process_queue
from app.services.project_store import project_store
from app.utils.file_utils import generate_project_id, resolve_storage_path
from app.utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/process-model", response_model=ProcessJobResponse)
async def process_model(request: ProcessModelRequest):
    """
    Queue papercraft pipeline processing for a project.

    Returns 202 Accepted with jobId — poll GET /api/process-jobs/{jobId}
    or GET /api/jobs/{jobId} for progress and results.
    """
    project = project_store.get(request.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.source_file_url:
        raise HTTPException(status_code=400, detail="Project has no uploaded model.")

    source_path = resolve_storage_path(project.source_file_url)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="Source model file not found.")

    existing = process_job_store.get_by_project(request.project_id)
    if existing and existing.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        body = build_process_job_response(existing)
        return JSONResponse(status_code=202, content=body.model_dump(by_alias=True))

    now = datetime.now(timezone.utc)
    job_id = generate_project_id()
    job = ProcessJob(
        id=job_id,
        projectId=request.project_id,
        settings=request.settings,
        projectName=project.name,
        sourcePath=str(source_path.resolve()),
        createdAt=now,
        updatedAt=now,
    )
    process_job_store.create(job)

    project.status = ProjectStatus.PROCESSING
    project.settings = request.settings
    project_store.update(project)

    await process_queue.enqueue(job_id)
    logger.info("Queued process job %s for project %s", job_id, project.id)

    body = build_process_job_response(job)
    return JSONResponse(status_code=202, content=body.model_dump(by_alias=True))


@router.get("/process-jobs/{job_id}", response_model=ProcessJobResponse)
async def get_process_job(job_id: str) -> ProcessJobResponse:
    """Poll async papercraft processing job status and results."""
    job = process_job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Process job not found.")
    return build_process_job_response(job)


@router.post("/process-jobs/{job_id}/cancel", response_model=ProcessJobResponse)
async def cancel_process_job(job_id: str) -> ProcessJobResponse:
    """Cancel a queued job or request cancellation of a running job."""
    job = process_job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Process job not found.")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail=f"Job already {job.status.value}.",
        )

    updated = process_job_store.cancel(job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Process job not found.")

    return build_process_job_response(updated)


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Return project metadata by ID."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.model_dump(by_alias=True)


@router.get(
    "/projects/{project_id}/generation-job",
    response_model=GenerationJobResponse,
)
async def get_project_generation_job(project_id: str) -> GenerationJobResponse:
    """Return the latest AI generation job for a project (for resume after reload)."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    job = generation_job_store.get_by_project(project_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="No generation job found for this project.",
        )

    return build_generation_job_response(job)


@router.get(
    "/projects/{project_id}/process-job",
    response_model=ProcessJobResponse,
)
async def get_project_process_job(project_id: str) -> ProcessJobResponse:
    """Return the latest papercraft process job for a project (for resume after reload)."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    job = process_job_store.get_by_project(project_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail="No process job found for this project.",
        )

    return build_process_job_response(job)
