"""File and path utilities."""

from __future__ import annotations

import struct
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

_READ_CHUNK_SIZE = 1024 * 1024


def generate_project_id() -> str:
    """Generate a unique project identifier."""
    return uuid.uuid4().hex[:12]


def _validate_model_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = Path(filename).suffix.lower()
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


async def read_upload_with_limit(
    file: UploadFile,
    *,
    max_bytes: int,
    empty_detail: str = "Uploaded file is empty.",
) -> bytes:
    """Stream an upload into memory, rejecting empty files and oversize payloads."""
    if max_bytes <= 0:
        raise HTTPException(status_code=500, detail="Upload size limit is not configured.")

    content_length = getattr(file, "size", None)
    if content_length is not None and content_length > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
        )

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        raise HTTPException(status_code=400, detail=empty_detail)
    return content


def validate_model_content(content: bytes, extension: str) -> None:
    """Verify file bytes match the declared 3D model extension."""
    validators = {
        ".obj": _looks_like_obj,
        ".stl": _looks_like_stl,
        ".glb": _looks_like_glb,
        ".gltf": _looks_like_gltf,
    }
    validator = validators.get(extension)
    if validator is None or not validator(content):
        raise HTTPException(
            status_code=400,
            detail=(
                f"File content does not match the '{extension}' format. "
                "Upload a valid OBJ, STL, GLB, or GLTF file."
            ),
        )


def validate_upload_file(file: UploadFile) -> str:
    """
    Validate uploaded file extension and return normalized extension.

    Raises HTTPException if the file type is not allowed.
    """
    return _validate_model_extension(file.filename)


async def read_and_validate_model_upload(file: UploadFile) -> tuple[str, bytes]:
    """Validate extension, enforce size limit, and verify model magic bytes."""
    extension = _validate_model_extension(file.filename)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await read_upload_with_limit(
        file,
        max_bytes=max_bytes,
        empty_detail="Uploaded model file is empty.",
    )
    validate_model_content(content, extension)
    return extension, content


def _looks_like_glb(content: bytes) -> bool:
    if len(content) < 12 or content[:4] != b"glTF":
        return False
    version = struct.unpack_from("<I", content, 4)[0]
    declared_length = struct.unpack_from("<I", content, 8)[0]
    return version in (1, 2) and declared_length == len(content)


def _looks_like_gltf(content: bytes) -> bool:
    try:
        text = content[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return False
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        return False
    lowered = stripped.lower()
    return '"asset"' in lowered and '"version"' in lowered


def _looks_like_obj(content: bytes) -> bool:
    if b"\x00" in content[:8192]:
        return False
    try:
        text = content[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return False

    obj_tokens = {"v", "vn", "vt", "f", "o", "g", "usemtl", "mtllib", "s"}
    for line in text.splitlines()[:50]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        token = stripped.split(maxsplit=1)[0].lower()
        if token in obj_tokens:
            return True
    return False


def _looks_like_ascii_stl(content: bytes) -> bool:
    try:
        head = content[:4096].decode("utf-8")
    except UnicodeDecodeError:
        return False
    stripped = head.lstrip()
    if not stripped.lower().startswith("solid"):
        return False
    lowered = head.lower()
    return "facet" in lowered and "vertex" in lowered


def _looks_like_binary_stl(content: bytes) -> bool:
    if len(content) < 84:
        return False
    triangle_count = struct.unpack_from("<I", content, 80)[0]
    expected_size = 84 + triangle_count * 50
    return len(content) == expected_size


def _looks_like_stl(content: bytes) -> bool:
    if _looks_like_ascii_stl(content):
        return True
    return _looks_like_binary_stl(content)


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

    try:
        path.relative_to(storage_root)
    except ValueError as exc:
        raise ValueError("Storage path escapes storage root.") from exc

    if path == storage_root:
        raise ValueError("Storage path escapes storage root.")

    return path
