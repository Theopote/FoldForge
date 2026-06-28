"""Validate and apply seam graph edits."""

from __future__ import annotations

import trimesh

from app.schemas.model import Difficulty
from app.services.seam_generator import (
    MAX_FACES_PER_PATCH,
    _edge_key,
    compute_edge_dihedral_angles,
    split_into_patches,
)


def validate_seam_set(
    mesh: trimesh.Trimesh,
    seams: set[tuple[int, int]],
    difficulty: Difficulty,
) -> str | None:
    """Return an error message when the seam set is invalid."""
    dihedral = compute_edge_dihedral_angles(mesh)
    max_faces = MAX_FACES_PER_PATCH[difficulty]

    for edge in seams:
        if edge not in dihedral.unsigned:
            return f"Edge {edge[0]},{edge[1]} is not an interior mesh edge."

    patches = split_into_patches(mesh, seams)
    if not patches:
        return "Seam set produced no patches."

    for patch in patches:
        if len(patch) > max_faces:
            return (
                f"A patch would contain {len(patch)} faces "
                f"(maximum {max_faces} for {difficulty.value} mode)."
            )

    return None


def apply_seam_toggle(
    mesh: trimesh.Trimesh,
    seams: set[tuple[int, int]],
    edge: tuple[int, int],
    difficulty: Difficulty,
) -> tuple[set[tuple[int, int]], str | None]:
    """Add or remove one seam edge. Returns (new_seams, error_message)."""
    key = _edge_key(edge[0], edge[1])
    dihedral = compute_edge_dihedral_angles(mesh)
    if key not in dihedral.unsigned:
        return seams, f"Edge {key[0]},{key[1]} is not an interior mesh edge."

    if key in seams:
        candidate = set(seams)
        candidate.discard(key)
    else:
        candidate = set(seams)
        candidate.add(key)

    error = validate_seam_set(mesh, candidate, difficulty)
    if error is not None:
        return seams, error
    return candidate, None
