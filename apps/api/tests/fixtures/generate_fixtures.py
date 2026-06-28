"""Generate committed mesh fixtures for pipeline tests. Run: python tests/fixtures/generate_fixtures.py"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

FIXTURES_DIR = Path(__file__).resolve().parent


def cube_stl() -> None:
    mesh = trimesh.creation.box(extents=(40.0, 40.0, 40.0))
    mesh.export(FIXTURES_DIR / "cube.stl")


def low_poly_bunny_obj() -> None:
    # Placeholder low-poly organic mesh (20-face icosphere) until a real bunny is added.
    mesh = trimesh.creation.icosphere(subdivisions=0, radius=30.0)
    mesh.export(FIXTURES_DIR / "low_poly_bunny.obj")


def simple_house_glb() -> None:
    base = trimesh.creation.box(extents=(60.0, 50.0, 35.0))
    base.apply_translation((0.0, 0.0, 17.5))
    roof = trimesh.creation.box(extents=(64.0, 54.0, 12.0))
    roof.apply_translation((0.0, 0.0, 41.0))
    chimney = trimesh.creation.box(extents=(8.0, 8.0, 18.0))
    chimney.apply_translation((18.0, 12.0, 56.0))
    house = trimesh.util.concatenate([base, roof, chimney])
    house.export(FIXTURES_DIR / "simple_house.glb")


def non_manifold_bad_mesh_stl() -> None:
    mesh = trimesh.creation.box(extents=(30.0, 30.0, 30.0))
    # Drop one face (open boundary) and duplicate an edge (non-manifold).
    faces = mesh.faces.copy()
    faces = np.delete(faces, 0, axis=0)
    faces = np.vstack([faces, faces[0:1]])
    mesh.faces = faces
    mesh.remove_unreferenced_vertices()
    mesh.export(FIXTURES_DIR / "non_manifold_bad_mesh.stl")


def thin_parts_model_obj() -> None:
    wall = trimesh.creation.box(extents=(80.0, 60.0, 1.5))
    fin = trimesh.creation.box(extents=(40.0, 1.5, 25.0))
    fin.apply_translation((0.0, 30.0, 13.0))
    spar = trimesh.creation.box(extents=(1.5, 50.0, 20.0))
    spar.apply_translation((35.0, 0.0, 10.0))
    mesh = trimesh.util.concatenate([wall, fin, spar])
    mesh.export(FIXTURES_DIR / "thin_parts_model.obj")


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    cube_stl()
    low_poly_bunny_obj()
    simple_house_glb()
    non_manifold_bad_mesh_stl()
    thin_parts_model_obj()
    print(f"Wrote fixtures to {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
