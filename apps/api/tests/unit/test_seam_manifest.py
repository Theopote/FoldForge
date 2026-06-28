"""Seam manifest export tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.geometry import CutLine, FoldLine, LayoutPage, PlacedPiece, Point2D, UnfoldPiece
from app.schemas.model import ProjectSettings
from app.services.seam_generator import compute_edge_dihedral_angles
from app.services.seam_manifest import build_seam_manifest, export_seam_manifest
from app.services.svg_exporter import export_svg
import trimesh


def _sample_page(piece: UnfoldPiece) -> LayoutPage:
    return LayoutPage(
        index=0,
        width_mm=210,
        height_mm=297,
        placed_pieces=[PlacedPiece(piece=piece, offset_x=10, offset_y=10, page_index=0)],
    )


def test_build_seam_manifest_indexes_cut_and_fold_edges() -> None:
    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(20, 0), Point2D(10, 20)],
        label="A",
        cut_lines=[
            CutLine(
                id="cut-a",
                start=Point2D(0, 0),
                end=Point2D(20, 0),
                mesh_edge=(1, 2),
            )
        ],
        fold_lines=[
            FoldLine(
                id="fold-a",
                start=Point2D(10, 0),
                end=Point2D(10, 20),
                fold_type="valley",
                mesh_edge=(0, 1),
            )
        ],
    )
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    manifest = build_seam_manifest([piece], dihedral)

    assert manifest["edgeCount"] == 2
    assert manifest["edges"]["1,2"]["kind"] == "cut"
    assert manifest["edges"]["0,1"]["kind"] == "fold"
    assert manifest["edges"]["1,2"]["pieceLabel"] == "A"


def test_export_svg_includes_seam_hit_target_layer(tmp_path: Path) -> None:
    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(20, 0), Point2D(10, 20)],
        label="A",
        cut_lines=[
            CutLine(
                id="cut-a",
                start=Point2D(0, 0),
                end=Point2D(20, 0),
                mesh_edge=(0, 1),
            )
        ],
        fold_lines=[
            FoldLine(
                id="fold-a",
                start=Point2D(10, 0),
                end=Point2D(10, 20),
                fold_type="mountain",
                mesh_edge=(1, 2),
            )
        ],
    )
    svg_path = tmp_path / "unfold.svg"
    export_svg([_sample_page(piece)], svg_path, "Seam Demo", ProjectSettings())

    content = svg_path.read_text(encoding="utf-8")
    assert 'class="layer-seams"' in content
    assert 'class="seam-edge seam-cut"' in content
    assert 'data-mesh-edge="0,1"' in content
    assert 'data-edge-kind="cut"' in content
    assert 'data-piece-label="A"' in content


def test_export_seam_manifest_writes_json(tmp_path: Path) -> None:
    piece = UnfoldPiece(
        id="piece-a",
        face_ids=[0],
        polygon=[Point2D(0, 0), Point2D(20, 0), Point2D(10, 20)],
        label="A",
        cut_lines=[
            CutLine(
                id="cut-a",
                start=Point2D(0, 0),
                end=Point2D(20, 0),
                mesh_edge=(0, 1),
            )
        ],
    )
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    dihedral = compute_edge_dihedral_angles(mesh)
    path = tmp_path / "demo.seams.json"
    export_seam_manifest(path, [piece], dihedral)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert "0,1" in payload["edges"]
