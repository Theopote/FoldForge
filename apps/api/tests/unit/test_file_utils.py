"""Upload validation tests."""

from __future__ import annotations

import io

import pytest
from fastapi import UploadFile

from app.utils.file_utils import validate_upload_file


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


def test_validate_rejects_fbx_as_experimental() -> None:
    upload = UploadFile(filename="character.fbx", file=io.BytesIO(b""))
    with pytest.raises(Exception) as exc_info:
        validate_upload_file(upload)
    assert "experimental" in str(exc_info.value.detail).lower()


def test_validate_rejects_unknown_extension() -> None:
    upload = UploadFile(filename="model.blend", file=io.BytesIO(b""))
    with pytest.raises(Exception) as exc_info:
        validate_upload_file(upload)
    assert "Unsupported" in str(exc_info.value.detail)
