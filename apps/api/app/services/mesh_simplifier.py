"""Mesh simplification and scaling based on difficulty and target size."""

import numpy as np
import trimesh

from app.schemas.model import Difficulty, Style

# Target face counts per difficulty (from product spec)
DIFFICULTY_FACE_TARGETS: dict[Difficulty, int] = {
    Difficulty.EASY: 100,
    Difficulty.STANDARD: 300,
    Difficulty.ADVANCED: 800,
}

STYLE_FACE_MULTIPLIER: dict[Style, float] = {
    Style.LOW_POLY: 1.0,
    Style.CUTE: 0.85,
    Style.GEOMETRIC: 1.15,
}


def scale_to_target_height(mesh: trimesh.Trimesh, target_height_mm: float) -> trimesh.Trimesh:
    """Uniformly scale mesh so its tallest axis matches target_height_mm."""
    scaled = mesh.copy()
    extents = scaled.bounding_box.extents
    current_height = float(np.max(extents))

    if current_height <= 1e-8:
        return scaled

    scale_factor = target_height_mm / current_height
    scaled.apply_scale(scale_factor)
    return scaled


def simplify_mesh(
    mesh: trimesh.Trimesh,
    difficulty: Difficulty,
    style: Style,
) -> trimesh.Trimesh:
    """
    Reduce face count toward difficulty target while preserving overall shape.

    Uses quadric decimation when available; falls back to iterative decimation.
    """
    target_faces = int(
        DIFFICULTY_FACE_TARGETS[difficulty] * STYLE_FACE_MULTIPLIER[style],
    )
    target_faces = max(target_faces, 12)

    if len(mesh.faces) <= target_faces:
        return mesh.copy()

    simplified = mesh.copy()

    try:
        simplified = simplified.simplify_quadric_decimation(target_faces)
    except Exception:
        # Fallback: progressively decimate toward target
        while len(simplified.faces) > target_faces and len(simplified.faces) > 12:
            next_target = max(
                target_faces,
                int(len(simplified.faces) * 0.75),
            )
            try:
                simplified = simplified.simplify_quadric_decimation(next_target)
            except Exception:
                break

    if len(simplified.faces) == 0:
        return mesh.copy()

    return simplified
