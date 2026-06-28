"""Export seam metadata for interactive SVG inspection in Studio."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import trimesh

from app.models.geometry import UnfoldPiece
from app.schemas.model import Difficulty
from app.services.seam_advisor import build_seam_advisor
from app.services.seam_generator import EdgeDihedralData
from app.services.seam_store import format_seam_list

MANIFEST_VERSION = 2


def build_seam_manifest(
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
    *,
    mesh: trimesh.Trimesh | None = None,
    active_seams: set[tuple[int, int]] | None = None,
    difficulty: Difficulty = Difficulty.STANDARD,
) -> dict[str, Any]:
    """Build a mesh-edge keyed manifest describing cut and fold lines on each piece."""
    edges: dict[str, dict[str, Any]] = {}
    seam_set = active_seams or set()

    for piece in pieces:
        for cut in piece.cut_lines:
            if cut.mesh_edge is None:
                continue
            key = _mesh_edge_key(cut.mesh_edge)
            unsigned = dihedral.unsigned.get(cut.mesh_edge, 0.0)
            signed = dihedral.signed.get(cut.mesh_edge, 0.0)
            edges[key] = _edge_entry(
                kind="cut",
                piece=piece,
                line_id=cut.id,
                mesh_edge=cut.mesh_edge,
                mesh=mesh,
                dihedral_unsigned=unsigned,
                dihedral_signed=signed,
                in_seam_set=cut.mesh_edge in seam_set,
            )

        for fold in piece.fold_lines:
            if fold.mesh_edge is None:
                continue
            key = _mesh_edge_key(fold.mesh_edge)
            if key in edges:
                continue
            unsigned = dihedral.unsigned.get(fold.mesh_edge, 0.0)
            signed = dihedral.signed.get(fold.mesh_edge, 0.0)
            edges[key] = _edge_entry(
                kind="fold",
                piece=piece,
                line_id=fold.id,
                mesh_edge=fold.mesh_edge,
                mesh=mesh,
                dihedral_unsigned=unsigned,
                dihedral_signed=signed,
                fold_type=fold.fold_type,
                in_seam_set=fold.mesh_edge in seam_set,
            )

    advisor: dict[str, Any] | None = None
    if mesh is not None and active_seams is not None:
        advisor = build_seam_advisor(
            mesh,
            pieces,
            active_seams,
            difficulty=difficulty,
            dihedral=dihedral,
        )

    return {
        "version": MANIFEST_VERSION,
        "edgeCount": len(edges),
        "activeSeams": format_seam_list(seam_set),
        "edges": edges,
        "advisor": advisor,
    }


def export_seam_manifest(
    output_path: Path,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
    *,
    mesh: trimesh.Trimesh | None = None,
    active_seams: set[tuple[int, int]] | None = None,
    difficulty: Difficulty = Difficulty.STANDARD,
) -> Path:
    """Write `{projectId}.seams.json` for Studio seam inspector tooltips."""
    payload = build_seam_manifest(
        pieces,
        dihedral,
        mesh=mesh,
        active_seams=active_seams,
        difficulty=difficulty,
    )
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _edge_entry(
    *,
    kind: str,
    piece: UnfoldPiece,
    line_id: str,
    mesh_edge: tuple[int, int],
    mesh: trimesh.Trimesh | None,
    dihedral_unsigned: float,
    dihedral_signed: float,
    in_seam_set: bool,
    fold_type: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kind": kind,
        "pieceId": piece.id,
        "pieceLabel": piece.label,
        "lineId": line_id,
        "dihedralDeg": round(math.degrees(dihedral_unsigned), 1),
        "signedDihedralDeg": round(math.degrees(dihedral_signed), 1),
        "hiddenCrease": dihedral_signed < -0.05,
        "inSeamSet": in_seam_set,
        "hasOverlap": piece.has_overlap,
    }
    if fold_type is not None:
        entry["foldType"] = fold_type
    if mesh is not None:
        v0, v1 = mesh_edge
        entry["position3d"] = {
            "a": [float(x) for x in mesh.vertices[v0]],
            "b": [float(x) for x in mesh.vertices[v1]],
        }
    return entry


def _mesh_edge_key(edge: tuple[int, int]) -> str:
    v0, v1 = edge
    if v0 > v1:
        v0, v1 = v1, v0
    return f"{v0},{v1}"
