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
from app.services.unfolder import (
    compute_unfold_vertex_map,
    find_overlapping_face_pairs,
    score_seams_by_overlap,
    unfold_mesh,
)


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
    face_heat = build_face_overlap_heat(mesh, pieces, dihedral)
    guidance = build_seam_guidance(
        pieces,
        seams,
        overlap_pieces,
        suggestions,
        edge_hints,
    )

    return {
        "overlapPieces": overlap_pieces,
        "suggestions": suggestions,
        "edgeHints": edge_hints,
        "faceHeat": face_heat,
        "guidance": guidance,
    }


def build_face_overlap_heat(
    mesh: trimesh.Trimesh,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
) -> dict[str, float]:
    """Per-face overlap intensity (0–1) for 3D heatmap overlay."""
    raw: dict[int, float] = {}

    for piece in pieces:
        if not piece.has_overlap:
            continue
        vertex_2d, _ = compute_unfold_vertex_map(mesh, piece.face_ids, dihedral)
        for f1, f2, area in find_overlapping_face_pairs(
            mesh, piece.face_ids, vertex_2d
        ):
            raw[f1] = raw.get(f1, 0.0) + area
            raw[f2] = raw.get(f2, 0.0) + area

    if not raw:
        return {}

    peak = max(raw.values())
    if peak <= 0:
        return {}

    return {str(face_idx): round(value / peak, 3) for face_idx, value in raw.items()}


def build_seam_guidance(
    pieces: list[UnfoldPiece],
    seams: set[tuple[int, int]],
    overlap_pieces: list[str],
    suggestions: list[dict[str, Any]],
    edge_hints: dict[str, dict[str, Any]],
) -> list[str]:
    """Human-readable craft hints for Studio seam advisor panel."""
    lines: list[str] = []

    if overlap_pieces:
        labels = ", ".join(overlap_pieces)
        lines.append(
            f"{len(overlap_pieces)} piece(s) overlap when unfolded ({labels}). "
            "Add cut seams along sharp interior edges to split those patches."
        )
    else:
        lines.append(
            "No unfold overlap detected. Merge adjacent cut seams only when "
            "pieces should stay connected in the flat layout."
        )

    if suggestions:
        top = suggestions[0]
        lines.append(
            f"Recommended next edit: {top['label']} — edge {top['meshEdge']}."
        )

    invalid = sum(
        1 for hint in edge_hints.values() if not hint.get("toggleValid", True)
    )
    if invalid:
        lines.append(
            f"{invalid} seam edge(s) cannot be toggled without breaking mesh "
            "connectivity — try a neighboring sharp edge instead."
        )

    fold_count = sum(1 for piece in pieces for fold in piece.fold_lines if fold.mesh_edge)
    cut_count = len(seams)
    lines.append(
        f"Current layout: {len(pieces)} piece(s), {cut_count} cut seam(s), "
        f"{fold_count} visible fold line(s)."
    )

    return lines[:4]


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
                "reason": _suggestion_reason(edge, action, score, dihedral),
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


def _suggestion_reason(
    edge: tuple[int, int],
    action: str,
    score: float,
    dihedral: EdgeDihedralData,
) -> str:
    degrees = math.degrees(dihedral.unsigned.get(edge, 0.0))
    if action == "add" and score >= 10:
        return "High overlap relief — splitting this patch should flatten cleanly."
    if action == "add" and degrees >= 45:
        return "Sharp dihedral — natural place to separate overlapping regions."
    if action == "add":
        return "Moderate score — try this seam if overlap persists after sharper cuts."
    return "Low-angle edge — merging may simplify assembly without new overlap."


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
