"""File and path utilities."""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


def generate_project_id() -> str:
    """Generate a unique project identifier."""
    return uuid.uuid4().hex[:12]


def validate_upload_file(file: UploadFile) -> str:
    """
    Validate uploaded file extension and return normalized extension.

    Raises HTTPException if the file type is not allowed.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = Path(file.filename).suffix.lower()
    if extension not in settings.allowed_extensions:
        allowed = ", ".join(sorted(settings.allowed_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Allowed: {allowed}",
        )
    return extension


def build_storage_url(relative_path: Path) -> str:
    """Convert a storage path to a public URL served by StaticFiles."""
    return f"/storage/{relative_path.as_posix()}"
