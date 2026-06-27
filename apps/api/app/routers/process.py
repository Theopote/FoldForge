"""Model processing router."""

from fastapi import APIRouter, HTTPException

from app.schemas.model import ProjectStatus
from app.schemas.unfold import (
    CraftabilityScore,
    ProcessModelRequest,
    ProcessModelResponse,
    ProcessStats,
)
from app.services.papercraft_pipeline import run_pipeline
from app.services.project_store import project_store
from app.utils.file_utils import resolve_storage_path
from app.utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/process-model", response_model=ProcessModelResponse)
async def process_model(request: ProcessModelRequest) -> ProcessModelResponse:
    """
    Process an uploaded model into a printable unfold template.

    Runs the full geometry pipeline synchronously (MVP).
    """
    project = project_store.get(request.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.source_file_url:
        raise HTTPException(status_code=400, detail="Project has no uploaded model.")

    project.status = ProjectStatus.PROCESSING
    project.settings = request.settings
    project_store.update(project)

    try:
        source_path = resolve_storage_path(project.source_file_url)
        if not source_path.exists():
            raise HTTPException(status_code=404, detail="Source model file not found.")

        logger.info("Processing project %s from %s", project.id, source_path)

        result = run_pipeline(
            project_id=project.id,
            source_path=source_path,
            project_name=project.name,
            settings=request.settings,
        )

        project.status = ProjectStatus.READY
        project.processed_model_url = result.processed_mesh_path
        project.unfold_svg_url = result.svg_path
        project.unfold_pdf_url = result.pdf_path
        project.settings = request.settings
        project_store.update(project)

        return ProcessModelResponse(
            projectId=project.id,
            status=ProjectStatus.READY,
            processedModelUrl=result.processed_mesh_path,
            unfoldSvgUrl=result.svg_path,
            unfoldPdfUrl=result.pdf_path,
            stats=ProcessStats(
                faces=result.face_count,
                pieces=len(result.pieces),
                pages=len(result.pages),
                difficultyScore=result.difficulty_score,
            ),
            craftability=CraftabilityScore(
                score=result.craftability_score,
                level=result.craftability_level,
                warnings=result.warnings,
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Processing failed for project %s", project.id)
        project.status = ProjectStatus.FAILED
        project_store.update(project)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {exc}",
        ) from exc


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Return project metadata by ID."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project.model_dump(by_alias=True)
