"""Load 3D mesh files into a unified Trimesh representation."""

from pathlib import Path

import numpy as np
import trimesh


def load_mesh(path: Path) -> trimesh.Trimesh:
    """
    Load OBJ / STL / GLB and return a single Trimesh.

    Raises ValueError if the file cannot be loaded as a mesh.
    """
    loaded = trimesh.load(path, force="mesh", process=False)

    if isinstance(loaded, trimesh.Scene):
        geometries = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if not geometries:
            raise ValueError("Scene contains no mesh geometry.")
        loaded = trimesh.util.concatenate(geometries)

    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError(f"Unsupported mesh type from {path}")

    if loaded.vertices is None or len(loaded.vertices) == 0:
        raise ValueError("Mesh has no vertices.")

    if loaded.faces is None or len(loaded.faces) == 0:
        raise ValueError("Mesh has no faces.")

    return loaded


def mesh_stats(mesh: trimesh.Trimesh) -> dict[str, float | int]:
    """Return basic mesh statistics for logging and scoring."""
    extents = mesh.bounding_box.extents
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "width_mm": float(extents[0]),
        "height_mm": float(extents[1]),
        "depth_mm": float(extents[2]),
    }
