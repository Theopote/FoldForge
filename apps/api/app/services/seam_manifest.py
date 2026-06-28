"""Export seam metadata for interactive SVG inspection in Studio."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from app.models.geometry import UnfoldPiece
from app.services.seam_generator import EdgeDihedralData

MANIFEST_VERSION = 1


def build_seam_manifest(
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
) -> dict[str, Any]:
    """Build a mesh-edge keyed manifest describing cut and fold lines on each piece."""
    edges: dict[str, dict[str, Any]] = {}

    for piece in pieces:
        for cut in piece.cut_lines:
            if cut.mesh_edge is None:
                continue
            key = _mesh_edge_key(cut.mesh_edge)
            unsigned = dihedral.unsigned.get(cut.mesh_edge, 0.0)
            signed = dihedral.signed.get(cut.mesh_edge, 0.0)
            edges[key] = {
                "kind": "cut",
                "pieceId": piece.id,
                "pieceLabel": piece.label,
                "lineId": cut.id,
                "dihedralDeg": round(math.degrees(unsigned), 1),
                "signedDihedralDeg": round(math.degrees(signed), 1),
                "hiddenCrease": signed < -0.05,
            }

        for fold in piece.fold_lines:
            if fold.mesh_edge is None:
                continue
            key = _mesh_edge_key(fold.mesh_edge)
            if key in edges:
                continue
            unsigned = dihedral.unsigned.get(fold.mesh_edge, 0.0)
            signed = dihedral.signed.get(fold.mesh_edge, 0.0)
            edges[key] = {
                "kind": "fold",
                "pieceId": piece.id,
                "pieceLabel": piece.label,
                "lineId": fold.id,
                "foldType": fold.fold_type,
                "dihedralDeg": round(math.degrees(unsigned), 1),
                "signedDihedralDeg": round(math.degrees(signed), 1),
                "hiddenCrease": signed < -0.05,
            }

    return {
        "version": MANIFEST_VERSION,
        "edgeCount": len(edges),
        "edges": edges,
    }


def export_seam_manifest(
    output_path: Path,
    pieces: list[UnfoldPiece],
    dihedral: EdgeDihedralData,
) -> Path:
    """Write `{projectId}.seams.json` for Studio seam inspector tooltips."""
    payload = build_seam_manifest(pieces, dihedral)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _mesh_edge_key(edge: tuple[int, int]) -> str:
    v0, v1 = edge
    if v0 > v1:
        v0, v1 = v1, v0
    return f"{v0},{v1}"
