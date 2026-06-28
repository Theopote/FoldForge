"""Model upload router."""

from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.schemas.model import ProjectStatus, SourceType, UploadModelResponse
from app.services.project_store import project_store
from app.utils.file_utils import build_storage_url, generate_project_id, validate_upload_file

router = APIRouter()


@router.post("/upload-model", response_model=UploadModelResponse)
async def upload_model(file: UploadFile = File(...)) -> UploadModelResponse:
    """
    Accept a 3D model upload (OBJ / STL / GLB / GLTF) and create a project record.

    Returns projectId and storage URL for the uploaded source file.
    """
    extension = validate_upload_file(file)
    project_id = generate_project_id()
    filename = f"{project_id}{extension}"
    destination = settings.uploads_dir / filename

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )

    async with aiofiles.open(destination, "wb") as output:
        await output.write(content)

    relative = Path("uploads") / filename
    source_url = build_storage_url(relative)

    project_store.create(
        project_id=project_id,
        name=Path(file.filename or filename).stem,
        source_type=SourceType.UPLOAD_3D,
        source_file_url=source_url,
        status=ProjectStatus.UPLOADED,
    )

    return UploadModelResponse(
        projectId=project_id,
        sourceFileUrl=source_url,
        status=ProjectStatus.UPLOADED,
    )
