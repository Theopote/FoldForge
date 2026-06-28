"""Auto-repair loop: split overlapping patches and re-unfold."""

from __future__ import annotations

from dataclasses import dataclass

import trimesh

from app.schemas.model import Difficulty
from app.models.geometry import UnfoldPiece
from app.services.seam_generator import (
    EdgeDihedralData,
    compute_edge_dihedral_angles,
    find_best_split_seam_in_patch,
    select_seams,
    split_into_patches,
)
from app.services.unfolder import detect_unfold_overlaps, unfold_mesh

MAX_UNFOLD_REPAIR_ITERATIONS = 5


@dataclass
class UnfoldRepairResult:
    pieces: list[UnfoldPiece]
    seams: set[tuple[int, int]]
    patches: list[list[int]]
    repair_steps: int
    messages: list[str]


def unfold_with_auto_repair(
    mesh: trimesh.Trimesh,
    difficulty: Difficulty,
    dihedral: EdgeDihedralData | None = None,
    *,
    max_iterations: int = MAX_UNFOLD_REPAIR_ITERATIONS,
) -> UnfoldRepairResult:
    """
    Unfold mesh patches and iteratively add repair seams when overlaps remain.

    For each overlapping piece, adds a balanced split seam inside the patch,
    re-splits patches, and re-unfolds until clean or max iterations.
    """
    data = dihedral or compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, difficulty, dihedral=data)
    patches = split_into_patches(mesh, seams)
    pieces = unfold_mesh(mesh, patches, dihedral=data)

    messages: list[str] = []
    repair_steps = 0

    for _ in range(max_iterations):
        overlapping = [piece for piece in pieces if piece.has_overlap]
        if not overlapping:
            if repair_steps > 0:
                messages.append(
                    f"Auto-repair resolved unfold overlaps in {repair_steps} step(s)."
                )
            break

        added_any = False
        for piece in overlapping:
            edge = find_best_split_seam_in_patch(mesh, seams, piece.face_ids, data)
            if edge is not None and edge not in seams:
                seams.add(edge)
                added_any = True

        if not added_any:
            break

        repair_steps += 1
        patches = split_into_patches(mesh, seams)
        pieces = unfold_mesh(mesh, patches, dihedral=data)

    remaining = sum(1 for piece in pieces if piece.has_overlap)
    if remaining > 0:
        messages.append(
            f"{remaining} piece(s) still overlap after auto-repair — "
            "the template may not fold correctly. Try Easy mode or a simpler model."
        )

    return UnfoldRepairResult(
        pieces=pieces,
        seams=seams,
        patches=patches,
        repair_steps=repair_steps,
        messages=messages,
    )


def collect_unfold_warnings(pieces: list[UnfoldPiece], repair_messages: list[str]) -> list[str]:
    """Merge overlap warnings with auto-repair status messages."""
    return repair_messages + detect_unfold_overlaps(pieces)
