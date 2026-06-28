"""Seam edit suggestions and toggle preview hints."""

from __future__ import annotations

import math
from typing import Any

import trimesh

from app.models.geometry import UnfoldPiece
from app.schemas.model import Difficulty
from app.services.seam_editor import apply_seam_toggle
from app.services.seam_generator import (
    EdgeDihedralData,
    _seam_preference_score,
    find_best_split_seam_in_patch,
    split_into_patches,
)
from app.services.seam_store import format_mesh_edge
from app.services.unfolder import score_seams_by_overlap, unfold_mesh, compute_unfold_vertex_map


def build_seam_advisor(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    seams: set[tuple[int, int]],
    difficulty: Difficulty,
    dihedral: EdgeDihedralData,
) -> dict[str, Any]:
    """Return overlap summary and ranked seam edit suggestions."""
    overlap_pieces = sorted(
        {piece.label for piece in pieces if piece.has_overlap and piece.label}
    )
    suggestions = _rank_seam_suggestions(mesh, pieces, seams, difficulty, dihedral)
    edge_hints = _build_edge_toggle_hints(mesh, seams, pieces, difficulty, dihedral)

    return {
        "overlapPieces": overlap_pieces,
        "suggestions": suggestions,
        "edgeHints": edge_hints,
    }


def _rank_seam_suggestions(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    seams: set[tuple[int, int]],
    difficulty: Difficulty,
    dihedral: EdgeDihedralData,
) -> list[dict[str, Any]]:
    scored: dict[tuple[int, int], float] = {}

    for piece in pieces:
        if not piece.has_overlap:
            continue
        vertex_2d, _ = compute_unfold_vertex_map(mesh, piece.face_ids, dihedral)
        overlap_scores = score_seams_by_overlap(mesh, piece.face_ids, vertex_2d)
        for edge, area in overlap_scores.items():
            if edge in seams:
                continue
            scored[edge] = max(scored.get(edge, 0.0), area)

        split_edge = find_best_split_seam_in_patch(
            mesh,
            seams,
            piece.face_ids,
            dihedral,
            overlap_edge_scores=overlap_scores,
        )
        if split_edge is not None and split_edge not in seams:
            scored[split_edge] = scored.get(split_edge, 0.0) + 10.0

    for edge in dihedral.unsigned:
        if edge in seams:
            continue
        scored.setdefault(edge, _seam_preference_score(edge, dihedral))

    ranked = sorted(scored.items(), key=lambda item: item[1], reverse=True)[:5]
    suggestions: list[dict[str, Any]] = []
    for edge, score in ranked:
        action = "add" if edge not in seams else "remove"
        label = _suggestion_label(edge, action, dihedral)
        suggestions.append(
            {
                "meshEdge": format_mesh_edge(edge),
                "action": action,
                "score": round(score, 2),
                "label": label,
            }
        )
    return suggestions


def _suggestion_label(
    edge: tuple[int, int],
    action: str,
    dihedral: EdgeDihedralData,
) -> str:
    degrees = math.degrees(dihedral.unsigned.get(edge, 0.0))
    if action == "add":
        return f"Split along sharp edge ({degrees:.0f}°) to reduce overlap"
    return f"Merge across edge ({degrees:.0f}°)"


def _build_edge_toggle_hints(
    mesh: trimesh.Trimesh,
    seams: set[tuple[int, int]],
    pieces: list[UnfoldPiece],
    difficulty: Difficulty,
    dihedral: EdgeDihedralData,
) -> dict[str, dict[str, Any]]:
    hints: dict[str, dict[str, Any]] = {}
    candidate_edges: set[tuple[int, int]] = set(seams)

    for piece in pieces:
        for cut in piece.cut_lines:
            if cut.mesh_edge is not None:
                candidate_edges.add(cut.mesh_edge)
        for fold in piece.fold_lines:
            if fold.mesh_edge is not None:
                candidate_edges.add(fold.mesh_edge)

    for edge in candidate_edges:
        key = format_mesh_edge(edge)
        new_seams, error = apply_seam_toggle(mesh, seams, edge, difficulty)
        if error is not None:
            hints[key] = {"toggleValid": False, "error": error}
            continue

        preview_patches = split_into_patches(mesh, new_seams)
        preview_pieces = unfold_mesh(mesh, preview_patches, dihedral=dihedral)
        overlap_count = sum(1 for piece in preview_pieces if piece.has_overlap)
        hints[key] = {
            "toggleValid": True,
            "overlapPiecesAfter": overlap_count,
            "pieceCountAfter": len(preview_pieces),
        }

    return hints


def overlap_piece_labels(pieces: list[UnfoldPiece]) -> list[str]:
    return sorted(
        {piece.label for piece in pieces if piece.has_overlap and piece.label}
    )
