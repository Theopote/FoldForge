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
    if extension in settings.experimental_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Format '{extension}' is experimental and not supported in MVP "
                "(Trimesh FBX import is unreliable). Convert to OBJ, STL, GLB, or GLTF."
            ),
        )
    if extension not in settings.supported_extensions:
        allowed = ", ".join(ext.lstrip(".") for ext in sorted(settings.supported_extensions))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension}'. Supported: {allowed.upper()}",
        )
    return extension


def build_storage_url(relative_path: Path) -> str:
    """Convert a storage path to a public URL served by StaticFiles."""
    return f"/storage/{relative_path.as_posix()}"


def resolve_storage_path(storage_url: str) -> Path:
    """
    Resolve a /storage/... URL to an absolute filesystem path.

    Raises ValueError if the URL is not a valid storage path.
    """
    prefix = "/storage/"
    if not storage_url.startswith(prefix):
        raise ValueError(f"Invalid storage URL: {storage_url}")

    relative = storage_url[len(prefix):]
    path = (settings.storage_root / relative).resolve()
    storage_root = settings.storage_root.resolve()

    if not str(path).startswith(str(storage_root)):
        raise ValueError("Storage path escapes storage root.")

    return path
