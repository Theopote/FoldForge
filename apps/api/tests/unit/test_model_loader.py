"""Verify committed fixtures load through Trimesh."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.model_loader import load_mesh, mesh_stats


@pytest.mark.parametrize(
    "fixture_name",
    [
        "cube.stl",
        "low_poly_bunny.obj",
        "simple_house.glb",
        "non_manifold_bad_mesh.stl",
        "thin_parts_model.obj",
    ],
)
def test_load_fixture(fixtures_dir: Path, fixture_name: str) -> None:
    path = fixtures_dir / fixture_name
    if not path.exists():
        pytest.skip(f"Missing {fixture_name}")
    mesh = load_mesh(path)
    stats = mesh_stats(mesh)
    assert stats["vertices"] >= 3
    assert stats["faces"] >= 1
