"""Export download router."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.schemas.model import ProjectStatus
from app.services.project_store import project_store
from app.utils.file_utils import resolve_storage_path

router = APIRouter()


@router.get("/projects/{project_id}/export/pdf")
async def export_pdf(project_id: str) -> FileResponse:
    """Download PDF unfold template for a project."""
    project = _get_ready_project(project_id)
    if not project.unfold_pdf_url:
        raise HTTPException(status_code=404, detail="PDF export not available.")
    path = resolve_storage_path(project.unfold_pdf_url)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="PDF export file not found.")
    return FileResponse(path, media_type="application/pdf", filename=f"{project.name}.pdf")


@router.get("/projects/{project_id}/export/svg")
async def export_svg(project_id: str) -> FileResponse:
    """Download SVG unfold template for a project."""
    project = _get_ready_project(project_id)
    if not project.unfold_svg_url:
        raise HTTPException(status_code=404, detail="SVG export not available.")
    path = resolve_storage_path(project.unfold_svg_url)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="SVG export file not found.")
    return FileResponse(path, media_type="image/svg+xml", filename=f"{project.name}.svg")


@router.get("/projects/{project_id}/export/instructions-pdf")
async def export_instructions_pdf(project_id: str) -> FileResponse:
    """Download the assembly instructions PDF for a project."""
    project = _get_ready_project(project_id)
    path = settings.exports_dir / f"{project_id}.instructions.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Instructions PDF not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{project.name}-instructions.pdf",
    )


@router.get("/projects/{project_id}/export/zip")
async def export_zip(project_id: str) -> FileResponse:
    """Download ZIP bundle (PDF + SVG + model + README)."""
    project = _get_ready_project(project_id)
    if not project.unfold_zip_url:
        raise HTTPException(status_code=404, detail="ZIP export not available.")
    path = resolve_storage_path(project.unfold_zip_url)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="ZIP export file not found.")
    return FileResponse(path, media_type="application/zip", filename=f"{project.name}-kit.zip")


def _get_ready_project(project_id: str):
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.status != ProjectStatus.READY:
        raise HTTPException(status_code=409, detail="Project export is not ready.")
    return project
