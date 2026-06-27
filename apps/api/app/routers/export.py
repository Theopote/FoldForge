"""Export download router (stub — full export in Step 6)."""

from fastapi import APIRouter, HTTPException

from app.services.project_store import project_store

router = APIRouter()


@router.get("/projects/{project_id}/export/pdf")
async def export_pdf(project_id: str) -> dict:
    """Download PDF unfold template for a project."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.unfold_pdf_url:
        raise HTTPException(status_code=404, detail="PDF export not available yet.")
    return {"downloadUrl": project.unfold_pdf_url}


@router.get("/projects/{project_id}/export/svg")
async def export_svg(project_id: str) -> dict:
    """Download SVG unfold template for a project."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.unfold_svg_url:
        raise HTTPException(status_code=404, detail="SVG export not available yet.")
    return {"downloadUrl": project.unfold_svg_url}


@router.get("/projects/{project_id}/export/zip")
async def export_zip(project_id: str) -> dict:
    """Download ZIP bundle for a project."""
    project = project_store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    raise HTTPException(status_code=501, detail="ZIP export not implemented yet.")
