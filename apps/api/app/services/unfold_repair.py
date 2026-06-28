"""Auto-repair loop: split overlapping patches and re-unfold."""

from __future__ import annotations

from dataclasses import dataclass

import trimesh

from app.config import settings
from app.models.geometry import UnfoldPiece
from app.schemas.model import Difficulty
from app.services.cancel import CancelCheck, check_cancelled
from app.services.pipeline_errors import UnfoldRepairError
from app.services.seam_generator import (
    EdgeDihedralData,
    compute_edge_dihedral_angles,
    find_best_split_seam_in_patch,
    select_seams,
    split_into_patches,
)
from app.services.unfolder import (
    compute_unfold_vertex_map,
    detect_unfold_overlaps,
    score_seams_by_overlap,
    unfold_mesh,
)

MAX_UNFOLD_REPAIR_ITERATIONS = 5


@dataclass
class UnfoldRepairResult:
    pieces: list[UnfoldPiece]
    seams: set[tuple[int, int]]
    patches: list[list[int]]
    repair_steps: int
    messages: list[str]
    export_blocked: bool = False
    has_unfold_overlap: bool = False


def unfold_with_auto_repair(
    mesh: trimesh.Trimesh,
    difficulty: Difficulty,
    dihedral: EdgeDihedralData | None = None,
    *,
    max_iterations: int = MAX_UNFOLD_REPAIR_ITERATIONS,
    block_export_on_failure: bool | None = None,
    cancel_check: CancelCheck | None = None,
) -> UnfoldRepairResult:
    """
    Unfold mesh patches and iteratively add repair seams when overlaps remain.

    Seam selection prefers edges adjacent to the largest 2D face overlaps.

    Overlap policy (``block_export_on_failure``, default from settings):
    - Strict: unresolved overlaps raise ``UnfoldRepairError`` — no export.
    - Warning: pipeline continues; ``has_unfold_overlap=True``, ``export_blocked=False``.
    """
    data = dihedral or compute_edge_dihedral_angles(mesh)
    seams = select_seams(mesh, difficulty, dihedral=data)
    return unfold_with_custom_seams(
        mesh,
        seams,
        difficulty,
        dihedral=data,
        max_iterations=max_iterations,
        block_export_on_failure=block_export_on_failure,
        cancel_check=cancel_check,
    )


def unfold_with_custom_seams(
    mesh: trimesh.Trimesh,
    seams: set[tuple[int, int]],
    difficulty: Difficulty,
    dihedral: EdgeDihedralData | None = None,
    *,
    max_iterations: int = MAX_UNFOLD_REPAIR_ITERATIONS,
    block_export_on_failure: bool | None = None,
    cancel_check: CancelCheck | None = None,
    auto_repair: bool = True,
) -> UnfoldRepairResult:
    """Unfold using a caller-provided seam set, optionally running overlap repair."""
    if block_export_on_failure is None:
        block_export_on_failure = settings.block_export_on_unfold_overlap

    data = dihedral or compute_edge_dihedral_angles(mesh)
    patches = split_into_patches(mesh, seams)
    pieces = unfold_mesh(mesh, patches, dihedral=data)

    messages: list[str] = []
    repair_steps = 0

    if auto_repair:
        for _ in range(max_iterations):
            check_cancelled(cancel_check)
            overlapping = [piece for piece in pieces if piece.has_overlap]
            if not overlapping:
                if repair_steps > 0:
                    messages.append(
                        f"Auto-repair resolved unfold overlaps in {repair_steps} step(s)."
                    )
                break

            added_any = False
            for piece in overlapping:
                check_cancelled(cancel_check)
                vertex_2d, _ = compute_unfold_vertex_map(mesh, piece.face_ids, data)
                overlap_scores = score_seams_by_overlap(mesh, piece.face_ids, vertex_2d)
                edge = find_best_split_seam_in_patch(
                    mesh,
                    seams,
                    piece.face_ids,
                    data,
                    overlap_edge_scores=overlap_scores,
                )
                if edge is not None and edge not in seams:
                    seams.add(edge)
                    added_any = True

            if not added_any:
                break

            check_cancelled(cancel_check)
            repair_steps += 1
            patches = split_into_patches(mesh, seams)
            pieces = unfold_mesh(mesh, patches, dihedral=data)

    remaining = sum(1 for piece in pieces if piece.has_overlap)
    has_unfold_overlap = remaining > 0

    if has_unfold_overlap:
        messages.append(
            f"{remaining} piece(s) still overlap after auto-repair — "
            "the template may not fold correctly. Try Easy mode or a simpler model."
        )
        if block_export_on_failure:
            warning_text = collect_unfold_warnings(pieces, messages)
            raise UnfoldRepairError(
                "Unfold overlaps could not be fully repaired. "
                "Export blocked — try Easy mode or a simpler model.",
                warnings=warning_text,
            )

    return UnfoldRepairResult(
        pieces=pieces,
        seams=seams,
        patches=patches,
        repair_steps=repair_steps,
        messages=messages,
        export_blocked=False,
        has_unfold_overlap=has_unfold_overlap,
    )


def collect_unfold_warnings(pieces: list[UnfoldPiece], repair_messages: list[str]) -> list[str]:
    """Merge overlap warnings with auto-repair status messages."""
    return repair_messages + detect_unfold_overlaps(pieces)
