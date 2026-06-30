"""Upload validation tests."""

from __future__ import annotations

import io
import struct

import pytest
from fastapi import HTTPException, UploadFile

from app.utils.file_utils import (
    read_and_validate_model_upload,
    read_upload_with_limit,
    resolve_storage_path,
    validate_model_content,
    validate_upload_file,
)


def _minimal_glb() -> bytes:
    return b"glTF" + struct.pack("<II", 2, 12)


def _minimal_gltf() -> bytes:
    return b'{"asset":{"version":"2.0","generator":"test"}}'


def _minimal_obj() -> bytes:
    return b"# cube\nv 0 0 0\nv 1 0 0\nf 1 2 3\n"


def _minimal_ascii_stl() -> bytes:
    return (
        b"solid cube\n"
        b" facet normal 0 0 1\n"
        b"  outer loop\n"
        b"   vertex 0 0 0\n"
        b"   vertex 1 0 0\n"
        b"   vertex 0 1 0\n"
        b"  endloop\n"
        b" endfacet\n"
        b"endsolid cube\n"
    )


def _sample_for_extension(extension: str) -> bytes:
    samples = {
        ".obj": _minimal_obj(),
        ".stl": _minimal_ascii_stl(),
        ".glb": _minimal_glb(),
        ".gltf": _minimal_gltf(),
    }
    return samples[extension]


@pytest.mark.parametrize(
    ("filename", "expected_ext"),
    [
        ("model.obj", ".obj"),
        ("model.STL", ".stl"),
        ("kit.glb", ".glb"),
        ("scene.gltf", ".gltf"),
    ],
)
def test_validate_supported_extensions(filename: str, expected_ext: str) -> None:
    upload = UploadFile(filename=filename, file=io.BytesIO(b""))
    assert validate_upload_file(upload) == expected_ext


@pytest.mark.parametrize(
    ("extension",),
    [(".obj",), (".stl",), (".glb",), (".gltf",)],
)
def test_validate_model_content_accepts_real_payloads(extension: str) -> None:
    validate_model_content(_sample_for_extension(extension), extension)


def test_validate_model_content_rejects_extension_spoof() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_model_content(b"not a model", ".stl")
    assert "does not match" in exc_info.value.detail


def test_validate_rejects_fbx_as_experimental() -> None:
    upload = UploadFile(filename="character.fbx", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        validate_upload_file(upload)
    assert "experimental" in exc_info.value.detail.lower()


def test_validate_rejects_unknown_extension() -> None:
    upload = UploadFile(filename="model.blend", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        validate_upload_file(upload)
    assert "Unsupported" in exc_info.value.detail


@pytest.mark.asyncio
async def test_read_upload_with_limit_rejects_oversize() -> None:
    upload = UploadFile(filename="big.stl", file=io.BytesIO(b"x" * 10))
    with pytest.raises(HTTPException) as exc_info:
        await read_upload_with_limit(upload, max_bytes=5)
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_read_upload_with_limit_rejects_empty() -> None:
    upload = UploadFile(filename="empty.stl", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        await read_upload_with_limit(upload, max_bytes=1024)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_read_and_validate_model_upload_accepts_valid_stl() -> None:
    upload = UploadFile(
        filename="cube.stl",
        file=io.BytesIO(_minimal_ascii_stl()),
    )
    extension, content = await read_and_validate_model_upload(upload)
    assert extension == ".stl"
    assert content.startswith(b"solid")


@pytest.mark.asyncio
async def test_read_and_validate_model_upload_rejects_wrong_magic() -> None:
    upload = UploadFile(
        filename="fake.stl",
        file=io.BytesIO(b"plain text payload"),
    )
    with pytest.raises(HTTPException) as exc_info:
        await read_and_validate_model_upload(upload)
    assert "does not match" in exc_info.value.detail


def test_resolve_storage_path_rejects_prefix_sibling(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr("app.utils.file_utils.settings.storage_root", storage_root)

    escaped = f"/storage/../{storage_root.name}-evil/file.stl"
    with pytest.raises(ValueError, match="escapes storage root"):
        resolve_storage_path(escaped)
