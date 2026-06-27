"""Model processing router (stub — full pipeline in Step 5)."""

from fastapi import APIRouter, HTTPException

from app.schemas.model import ProjectStatus
from app.schemas.unfold import ProcessModelRequest, ProcessModelResponse
from app.services.project_store import project_store

router = APIRouter()


@router.post("/process-model", response_model=ProcessModelResponse)
async def process_model(request: ProcessModelRequest) -> ProcessModelResponse:
    """
    Process an uploaded model into a printable unfold template.

    MVP stub: validates project exists and returns processing-not-implemented status.
    Full geometry pipeline will be implemented in Step 5.
    """
    project = project_store.get(request.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    project.status = ProjectStatus.PROCESSING
    project.settings = request.settings
    project_store.update(project)

    # Placeholder — geometry services will replace this in Step 5
    return ProcessModelResponse(
        projectId=project.id,
        status=ProjectStatus.PROCESSING,
    )


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Return project metadata by ID."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.model_dump(by_alias=True)
